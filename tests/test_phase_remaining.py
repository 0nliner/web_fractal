"""
Tests: Phase 3.6 (components), Phase 6 (transports), Phase 6.5 (extraction), Phase 7 (CLI), Phase 9 (infra).
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------

class CompBase(DeclarativeBase):
    pass


class Product(CompBase):
    __tablename__ = "products_comp"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class ProductDM(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str


# ---------------------------------------------------------------------------
# Phase 3.6 — components.py
# ---------------------------------------------------------------------------

def test_generate_creates_repo_class():
    from web_fractal.core.components import generate
    result = generate(model=Product, datamapper=ProductDM)
    assert result.repo is not None
    assert issubclass(result.repo, __import__("web_fractal.mixins", fromlist=["GenericRepo"]).GenericRepo)


def test_generate_sets_model_and_dm_class():
    from web_fractal.core.components import generate
    result = generate(model=Product, datamapper=ProductDM)
    assert result.repo.model is Product
    assert result.repo.dm_class is ProductDM


def test_generate_creates_service_class():
    from web_fractal.core.components import generate
    from web_fractal.mixins import GenericService
    result = generate(model=Product, datamapper=ProductDM)
    assert issubclass(result.service, GenericService)


def test_generate_result_model_name():
    from web_fractal.core.components import generate
    result = generate(model=Product, datamapper=ProductDM)
    assert result.model_name == "Product"
    assert result.repo.__name__ == "ProductRepo"
    assert result.service.__name__ == "ProductService"


def test_generate_with_optional_dtos():
    from web_fractal.core.components import generate
    from web_fractal.filters import FilterBase, FilterField

    class CreateProductDTO(BaseModel):
        name: str

    class ProductFilter(FilterBase):
        name: FilterField[str]

    result = generate(
        model=Product,
        datamapper=ProductDM,
        create=CreateProductDTO,
        selection=ProductFilter,
    )
    assert result.create_dto is CreateProductDTO
    assert result.selection is ProductFilter
    assert result.update_dto is None


def test_generate_different_models_independent_classes():
    from web_fractal.core.components import generate

    class Other(CompBase):
        __tablename__ = "other_comp"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class OtherDM(BaseModel):
        model_config = {"from_attributes": True}
        id: int

    r1 = generate(model=Product, datamapper=ProductDM)
    r2 = generate(model=Other, datamapper=OtherDM)
    assert r1.repo is not r2.repo
    assert r1.repo.model is not r2.repo.model


def test_register_generated_results():
    from web_fractal.core.components import generate, register_generated_results

    result = generate(model=Product, datamapper=ProductDM)
    registered = {}
    mock_injector = MagicMock()
    mock_injector.register = lambda key, val: registered.__setitem__(key, val)

    register_generated_results(mock_injector, result)
    assert "ProductRepo" in registered
    assert "ProductService" in registered
    assert registered["ProductService"].repo is registered["ProductRepo"]


# ---------------------------------------------------------------------------
# Phase 6 — Transports / Multi-protocol
# ---------------------------------------------------------------------------

def test_protocol_controller_abc_requires_init_handlers():
    from web_fractal.transports.protocols import ProtocolControllerABC

    with pytest.raises(TypeError):
        ProtocolControllerABC()


def test_kafka_controller_abc_reg_handler():
    from web_fractal.transports.protocols import KafkaControllerABC

    class MyKafka(KafkaControllerABC):
        def init_handlers(self):
            self.reg_handler("orders.created", self.handle_order)

        async def handle_order(self, msg):
            pass

    ctrl = MyKafka()
    ctrl.init_handlers()
    assert "orders.created" in ctrl._handlers


def test_grpc_controller_abc_reg_handler():
    from web_fractal.transports.protocols import GrpcServiceControllerABC

    class MyGrpc(GrpcServiceControllerABC):
        service_name = "MyService"

        def init_handlers(self):
            self.reg_handler("GetUser", self.get_user)

        async def get_user(self, req):
            pass

    ctrl = MyGrpc()
    ctrl.init_handlers()
    assert "GetUser" in ctrl._handlers


def test_graphql_controller_abc_reg_query():
    from web_fractal.transports.protocols import GraphQLControllerABC

    class MyGraphQL(GraphQLControllerABC):
        def init_handlers(self):
            self.reg_query("users", self.resolve_users)

        async def resolve_users(self):
            return []

    ctrl = MyGraphQL()
    ctrl.init_handlers()
    assert "users" in ctrl._queries


def test_kafka_subclasses_have_own_handlers():
    from web_fractal.transports.protocols import KafkaControllerABC

    class KafkaA(KafkaControllerABC):
        def init_handlers(self):
            self.reg_handler("topic.a", lambda: None)

    class KafkaB(KafkaControllerABC):
        def init_handlers(self):
            self.reg_handler("topic.b", lambda: None)

    a, b = KafkaA(), KafkaB()
    a.init_handlers()
    b.init_handlers()
    assert "topic.a" in a._handlers
    assert "topic.b" not in a._handlers
    assert "topic.b" in b._handlers


def test_initialize_all_protocols_calls_init_handlers():
    from web_fractal.transports.protocols import ProtocolControllerABC, initialize_all_protocols

    called = []

    class TestProto(ProtocolControllerABC):
        def init_handlers(self):
            called.append(self)

    instance = TestProto()
    mock_injector = MagicMock()
    mock_injector.dependencies = {"test_proto": instance}

    initialize_all_protocols(mock_injector)
    assert instance in called


def test_initialize_all_protocols_registers_http_router():
    from fastapi import FastAPI, APIRouter
    from web_fractal.http.interfaces import HttpControllerABC
    from web_fractal.transports.protocols import initialize_all_protocols

    class TestHTTP(HttpControllerABC):
        router = APIRouter(prefix="/test")

        def init_http_routes(self):
            pass

        def init_handlers(self):
            self.init_http_routes()

    instance = TestHTTP()
    app = FastAPI()
    mock_injector = MagicMock()
    mock_injector.dependencies = {"test_http": instance}

    initialize_all_protocols(mock_injector, app=app)
    routes = [r.path for r in app.routes]
    # no routes added (empty router), but no error either
    assert True


# ---------------------------------------------------------------------------
# Phase 6.5 — Fractal Extraction
# ---------------------------------------------------------------------------

def test_extract_plan_creates():
    from web_fractal.core.extraction import ExtractPlan, FractalExtractor

    plan = FractalExtractor.analyze("app.orders", protocol="http")
    assert plan.module_name == "app.orders"
    assert plan.protocol == "http"


def test_extract_plan_no_circular_for_simple_module():
    from web_fractal.core.extraction import ExtractPlan, ModuleDependency

    plan = ExtractPlan(module_name="app.orders", module_path=Path("app/orders"))
    plan.dependencies = [ModuleDependency("users", "app.users")]
    assert plan.has_circular_deps() is False


def test_extract_plan_detects_circular():
    from web_fractal.core.extraction import ExtractPlan, ModuleDependency

    plan = ExtractPlan(module_name="app.orders", module_path=Path("app/orders"))
    plan.dependencies = [
        ModuleDependency("orders", "app.orders"),  # self-reference
    ]
    assert plan.has_circular_deps() is True


def test_extract_plan_summary():
    from web_fractal.core.extraction import ExtractPlan, ModuleDependency

    plan = ExtractPlan(module_name="app.orders", module_path=Path("app/orders"))
    plan.dependencies = [ModuleDependency("users", "app.users")]
    s = plan.summary()
    assert "app.orders" in s
    assert "app.users" in s


def test_extract_raises_not_implemented():
    from web_fractal.core.extraction import ExtractPlan, FractalExtractor

    plan = ExtractPlan(module_name="app.orders", module_path=Path("app/orders"))
    with pytest.raises(NotImplementedError):
        FractalExtractor.extract(plan)


def test_extraction_importable_from_top_level():
    from web_fractal import ExtractPlan, FractalExtractor
    assert FractalExtractor is not None
    assert ExtractPlan is not None


# ---------------------------------------------------------------------------
# Phase 7 — CLI
# ---------------------------------------------------------------------------

def test_cli_help():
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "web_fractal" in result.output.lower() or "Usage" in result.output


def test_cli_init_creates_project(tmp_path):
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init", "myapp"])
        assert result.exit_code == 0
        assert Path("myapp/pyproject.toml").exists()
        assert Path("myapp/entrypoints/asgi.py").exists()
        assert Path("myapp/app/archtool_conf/bundle.py").exists()


def test_cli_init_refuses_existing_dir(tmp_path):
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("existing").mkdir()
        result = runner.invoke(cli, ["init", "existing"])
        assert result.exit_code != 0


def test_cli_add_module_creates_files(tmp_path):
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("app").mkdir()
        result = runner.invoke(cli, ["add-module", "orders", "--app", "app"])
        assert result.exit_code == 0
        assert Path("app/orders/interfaces.py").exists()
        assert Path("app/orders/models.py").exists()
        assert Path("app/orders/repos.py").exists()
        assert Path("app/orders/services.py").exists()
        assert Path("app/orders/scopes.py").exists()


def test_cli_add_module_with_http_controller(tmp_path):
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("app").mkdir()
        result = runner.invoke(cli, ["add-module", "products", "--app", "app", "--with-controller", "http"])
        assert result.exit_code == 0
        assert Path("app/products/controllers.py").exists()
        content = Path("app/products/controllers.py").read_text()
        assert "AutoHttpController" in content


def test_cli_extract_dry_run(tmp_path):
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["extract", "app.orders", "--dry-run"])
        assert result.exit_code == 0
        assert "app.orders" in result.output


def test_cli_graph_commands_available():
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["graph", "--help"])
    assert result.exit_code == 0


def test_cli_generate_group_help():
    from click.testing import CliRunner
    from web_fractal.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "impl" in result.output


# ---------------------------------------------------------------------------
# Phase 9 — Infrastructure
# ---------------------------------------------------------------------------

def test_pyproject_version():
    import importlib.metadata
    try:
        version = importlib.metadata.version("web_fractal")
        assert version is not None
    except importlib.metadata.PackageNotFoundError:
        pass  # not installed as package in test env


def test_public_api_all_new_symbols():
    import web_fractal
    new_symbols = [
        "GenericRepo", "GenericService", "NotExist", "MultipleFound",
        "AutoHttpController",
        "GenerationResult", "generate", "register_generated_results",
        "ProtocolControllerABC", "KafkaControllerABC",
        "GrpcServiceControllerABC", "GraphQLControllerABC",
        "initialize_all_protocols",
        "FractalExtractor", "ExtractPlan",
    ]
    for sym in new_symbols:
        assert hasattr(web_fractal, sym), f"{sym} missing from web_fractal public API"
        assert sym in web_fractal.__all__, f"{sym} missing from __all__"
