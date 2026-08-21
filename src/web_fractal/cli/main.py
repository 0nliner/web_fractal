"""
Phase 7: `wf` CLI — web_fractal project tooling.

Entry point declared in pyproject.toml:
    [project.scripts]
    wf = "web_fractal.cli.main:cli"

Commands:
    wf init <name>            — scaffold new project
    wf add-module <name>      — add domain module
    wf generate impl <module> — generate boilerplate from interfaces.py
    wf extract <module>       — extract module to microservice (dry-run by default)
    wf validate               — validate DI + protocol wiring
    wf graph                  — dependency graph
    wf diagram <target>       — build ER + class diagrams from existing code
"""
import sys
from pathlib import Path

import click


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="web_fractal")
def cli() -> None:
    """web_fractal project tooling."""


# ---------------------------------------------------------------------------
# wf init
# ---------------------------------------------------------------------------

@cli.command("init")
@click.argument("name")
@click.option("--protocols", "-p", multiple=True,
              type=click.Choice(["http", "kafka", "grpc", "graphql"]),
              default=("http",), show_default=True,
              help="Transport protocols to scaffold.")
def init(name: str, protocols: tuple) -> None:
    """Scaffold a new web_fractal project."""
    root = Path(name)
    if root.exists():
        click.echo(f"Error: directory '{name}' already exists.", err=True)
        sys.exit(1)

    _create_tree(root, {
        "pyproject.toml": _pyproject_template(name),
        "app/__init__.py": "",
        "app/config.py": "# project config\n",
        "app/archtool_conf/__init__.py": "",
        "app/archtool_conf/bundle.py": _bundle_template(name),
        "app/archtool_conf/custom_layers.py": _layers_template(),
        "app/archtool_conf/reg_deps.py": "# register dependencies here\n",
        "entrypoints/__init__.py": "",
        "entrypoints/asgi.py": _asgi_template(name),
        "migrations/env.py": "# alembic env\n",
        "tests/__init__.py": "",
        "tests/conftest.py": "# pytest fixtures\n",
    })
    click.echo(f"Project '{name}' created. cd {name} && uv sync")


# ---------------------------------------------------------------------------
# wf add-module
# ---------------------------------------------------------------------------

@cli.command("add-module")
@click.argument("name")
@click.option("--app", "app_path", default="app", show_default=True)
@click.option("--with-controller", type=click.Choice(["http", "kafka", "grpc", "graphql"]),
              default=None, help="Also generate a controller for this protocol.")
def add_module(name: str, app_path: str, with_controller: str) -> None:
    """Add a new domain module."""
    module_root = Path(app_path) / name
    if module_root.exists():
        click.echo(f"Error: module '{name}' already exists at {module_root}.", err=True)
        sys.exit(1)

    files = {
        "__init__.py": "",
        "interfaces.py": _interfaces_template(name),
        "models.py": _models_template(name),
        "dtos.py": _dtos_template(name),
        "repos.py": _repos_stub_template(name),
        "services.py": _services_stub_template(name),
        "scopes.py": _scopes_stub_template(name),
        "tests/__init__.py": "",
        "tests/test_{}.py".format(name): f"# tests for {name}\n",
    }
    if with_controller == "http":
        files["controllers.py"] = _http_controller_template(name)
    elif with_controller in ("kafka", "grpc", "graphql"):
        files["controllers.py"] = f"# {with_controller} controller for {name}\n"

    _create_tree(module_root, files)
    click.echo(f"Module '{name}' created at {module_root}.")


# ---------------------------------------------------------------------------
# wf generate
# ---------------------------------------------------------------------------

@cli.group("generate")
def generate() -> None:
    """Code generation commands."""


@generate.command("impl")
@click.argument("module")
@click.option("--dry-run", is_flag=True, help="Print what would be generated without writing files.")
def generate_impl(module: str, dry_run: bool) -> None:
    """Generate boilerplate implementations from a module's interfaces.py."""
    from web_fractal.core.components import generate as _generate

    parts = module.split(".")
    module_path = Path(*parts)

    if not module_path.exists():
        click.echo(f"Error: module path '{module_path}' not found.", err=True)
        sys.exit(1)

    interfaces_file = module_path / "interfaces.py"
    if not interfaces_file.exists():
        click.echo(f"Error: {interfaces_file} not found.", err=True)
        sys.exit(1)

    click.echo(f"Generating impl for {module}...")

    # Discover model and DM from module
    model_file = module_path / "models.py"
    dtos_file = module_path / "dtos.py"

    generated_files = []

    if model_file.exists() and dtos_file.exists():
        generated_files.append(module_path / "repos.py")
        generated_files.append(module_path / "services.py")

    if dry_run:
        click.echo("Would generate:")
        for f in generated_files:
            click.echo(f"  {f}")
    else:
        click.echo("Note: automatic model discovery requires explicit configuration.")
        click.echo("Use the generate() function directly in generated.py for runtime generation.")
        for f in generated_files:
            click.echo(f"  Would write: {f}")


# ---------------------------------------------------------------------------
# wf extract
# ---------------------------------------------------------------------------

@cli.command("extract")
@click.argument("module")
@click.option("--protocol", "-p",
              type=click.Choice(["http", "grpc", "kafka"]),
              default="http", show_default=True)
@click.option("--dry-run/--no-dry-run", default=True, show_default=True,
              help="Show extraction plan without making changes.")
def extract(module: str, protocol: str, dry_run: bool) -> None:
    """Extract a module to a standalone microservice."""
    from web_fractal.core.extraction import FractalExtractor

    plan = FractalExtractor.analyze(module, protocol=protocol)
    click.echo(plan.summary())

    if plan.has_circular_deps():
        click.echo("\nAborted: resolve circular dependencies first.", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("\nDry-run mode — no files written. Remove --dry-run to proceed.")
        return

    try:
        FractalExtractor.extract(plan)
    except NotImplementedError as e:
        click.echo(f"Not yet implemented: {e}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# wf validate
# ---------------------------------------------------------------------------

@cli.command("validate")
@click.option("--bundle", default="app.archtool_conf.bundle", show_default=True)
def validate(bundle: str) -> None:
    """Validate DI wiring and protocol controller registration."""
    try:
        import importlib
        mod = importlib.import_module(bundle)
        build_fn = getattr(mod, "build_injector", None)
        if build_fn is None:
            click.echo(f"Error: build_injector not found in {bundle}.", err=True)
            sys.exit(1)
        injector = build_fn()
        from web_fractal.building_utils import filter_objects_of_type
        from web_fractal.http.interfaces import HttpControllerABC

        controllers = filter_objects_of_type(injector, HttpControllerABC)
        click.echo(f"OK: {len(injector.dependencies)} dependencies registered.")
        click.echo(f"    {len(controllers)} HTTP controller(s) found.")
    except ImportError as e:
        click.echo(f"Import error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# wf graph
# ---------------------------------------------------------------------------

@cli.command("graph")
@click.option("--format", "fmt",
              type=click.Choice(["tree", "dot", "web"]),
              default="tree", show_default=True)
@click.option("--bundle", default="app.archtool_conf.bundle", show_default=True)
def graph(fmt: str, bundle: str) -> None:
    """Print the dependency graph."""
    try:
        import importlib
        mod = importlib.import_module(bundle)
        build_fn = getattr(mod, "build_injector", None)
        if build_fn is None:
            click.echo(f"Error: build_injector not found in {bundle}.", err=True)
            sys.exit(1)
        injector = build_fn()
        deps = (
            injector.dependencies
            if hasattr(injector, "dependencies")
            else getattr(injector, "_dependencies", {})
        )
    except Exception as e:
        click.echo(f"Error loading bundle: {e}", err=True)
        sys.exit(1)

    if fmt == "tree":
        for key, instance in deps.items():
            click.echo(f"{key}: {type(instance).__name__}")
    elif fmt == "dot":
        click.echo("digraph web_fractal {")
        for key in deps:
            click.echo(f'  "{key}";')
        click.echo("}")
    elif fmt == "web":
        click.echo("Web graph format: run `wf graph --format dot | dot -Tsvg > graph.svg`")


# ---------------------------------------------------------------------------
# wf diagram — reverse-engineer ER + class diagrams from existing code
# ---------------------------------------------------------------------------

@cli.command("diagram")
@click.argument("target")
@click.option("--kind", "-k", type=click.Choice(["er", "class", "both"]),
              default="both", show_default=True, help="Which diagram(s) to build.")
@click.option("--format", "-f", "fmt", type=click.Choice(["mermaid", "cad", "json"]),
              default="mermaid", show_default=True,
              help="mermaid — portable text; cad — fractal_cad JSON; json — raw model.")
@click.option("--out", "-o", "out", type=click.Path(), default=None,
              help="Write to file instead of stdout.")
def diagram(target: str, kind: str, fmt: str, out: str) -> None:
    """Build class and ER diagrams from existing code (static AST parse, no import).

    TARGET is a file, a directory, or a dotted module path (e.g. `app` or `app.crm`).
    """
    from web_fractal.core.diagram import build_diagrams, render

    try:
        model = build_diagrams(target)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if model.is_empty:
        click.echo("Nothing found: no SQLAlchemy tables and no classes in target.", err=True)
        sys.exit(1)

    text = render(model, fmt=fmt, kind=kind)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(
            f"Wrote {fmt} diagram → {out}  "
            f"({len(model.entities)} tables, {len(model.relations)} relations, {len(model.classes)} classes)"
        )
    else:
        click.echo(text)


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _create_tree(root: Path, files: dict) -> None:
    for rel_path, content in files.items():
        full = root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        if not full.exists():
            full.write_text(content)


def _pyproject_template(name: str) -> str:
    return f"""[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["web_fractal", "fastapi", "sqlalchemy[asyncio]", "pydantic>=2.0"]

[build-system]
requires = ["setuptools>=65"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
"""


def _bundle_template(name: str) -> str:
    return f"""from archtool import DependencyInjector
from .custom_layers import ApplicationLayer

def build_injector() -> DependencyInjector:
    injector = DependencyInjector(layers=[ApplicationLayer])
    return injector
"""


def _layers_template() -> str:
    return """from archtool import ComponentPattern, Layer
from web_fractal.http.interfaces import HttpControllerABC

APPS: list = []  # populate with your app modules

ApplicationLayer = Layer(
    name="application",
    components=[
        ComponentPattern("controllers", HttpControllerABC),
    ],
    apps=APPS,
)
"""


def _asgi_template(name: str) -> str:
    return f"""from fastapi import FastAPI
from web_fractal.building_utils import initialize_controllers_api
from app.archtool_conf.bundle import build_injector

app = FastAPI(title="{name}")
injector = build_injector()
initialize_controllers_api(injector, app)
"""


def _interfaces_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from abc import abstractmethod
from archtool.layers.default_layer_interfaces import ABCRepo, ABCService


class {cap}RepoABC(ABCRepo):
    @abstractmethod
    async def get_by_id(self, id: int): ...


class {cap}ServiceABC(ABCService):
    @abstractmethod
    async def get_by_id(self, id: int): ...
"""


def _models_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from web_fractal.db import Base, Dated


class {cap}(Base, Dated):
    __tablename__ = "{name}s"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
"""


def _dtos_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from web_fractal.dtos import Base


class {cap}DM(Base):
    id: int
    name: str


class Create{cap}DTO(Base):
    name: str


class Update{cap}DTO(Base):
    name: str | None = None
"""


def _repos_stub_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from sqlalchemy.ext.asyncio import async_sessionmaker
from web_fractal.mixins import GenericRepo
from .models import {cap}
from .dtos import {cap}DM
from .interfaces import {cap}RepoABC


class {cap}Repo({cap}RepoABC, GenericRepo):
    model = {cap}
    dm_class = {cap}DM
    session_maker: async_sessionmaker
"""


def _services_stub_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from web_fractal.mixins import GenericService
from .interfaces import {cap}ServiceABC
from .repos import {cap}Repo


class {cap}Service({cap}ServiceABC, GenericService):
    repo: {cap}Repo  # injected by archtool
"""


def _scopes_stub_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from web_fractal.core.security import AccessRule, FieldScope, FilterScope, RowRule, ScopeBase
from web_fractal.filters import Op


class {cap}Scope(ScopeBase, strict=False):
    # bypass_if = staticmethod(lambda ctx: "admin" in ctx.user.roles)
    # row_rule = RowRule(lambda ctx, m: m.org_id == ctx.user.organization_id)
    field_scopes: dict = {{}}
    filter_scopes: dict = {{}}
"""


def _http_controller_template(name: str) -> str:
    cap = name.capitalize()
    return f"""from fastapi import APIRouter
from web_fractal.http.auto_controller import AutoHttpController
from .interfaces import {cap}ServiceABC
from .dtos import {cap}DM, Create{cap}DTO


class {cap}Controller(AutoHttpController):
    router = APIRouter(prefix="/{name}s", tags=["{cap}s"])
    service: {cap}ServiceABC  # injected by archtool

    async def filter_{name}s(self) -> list[{cap}DM]:
        ...

    async def get_{name}(self, id: int) -> {cap}DM:
        ...

    async def create_{name}(self, data: Create{cap}DTO) -> {cap}DM:
        ...

    async def delete_{name}(self, id: int) -> None:
        ...
"""


if __name__ == "__main__":
    cli()
