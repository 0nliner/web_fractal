"""
archtool DI assembly.

build_injector() is the single entry point for both production (asgi.py)
and tests (conftest.py).  The injector scans each module's interfaces.py
for abstract ABCs, finds concrete implementations, and wires them.

session_maker is set after inject() because async_sessionmaker lives in
SQLAlchemy — outside the project root — so archtool cannot serialize it
as a dependency key.  Instead we set it directly on every repo and
controller that needs it.
"""
import pathlib
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from archtool.dependency_injector import DependencyInjector

from web_fractal.building_utils import import_all_models, initialize_controllers_api
from web_fractal.db import Base
from web_fractal.http.interfaces import HttpControllerABC
from web_fractal.mixins import GenericRepo

from .custom_layers import APPS

# Project root is examples/anki/ — where pyproject.toml lives
_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def build_injector(
    db_url: str = "",
    *,
    session_maker: Optional[async_sessionmaker] = None,
) -> tuple[DependencyInjector, Optional[AsyncEngine]]:
    engine: Optional[AsyncEngine] = None
    if session_maker is None:
        engine = create_async_engine(db_url, echo=False)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    injector = DependencyInjector(
        modules_list=APPS,
        project_root=_PROJECT_ROOT,
    )

    # import_all_models uses get_project_root() set by DependencyInjector above.
    # Calling it here ensures all ORM models are registered with Base.metadata
    # before create_all — without spelling out each import manually.
    import_all_models(Base)

    injector.inject()

    # Post-inject: wire session_maker onto every repo and controller.
    # Cannot annotate it — SQLAlchemy is outside project root.
    for instance in injector._dependencies.values():
        if isinstance(instance, (GenericRepo, HttpControllerABC)):
            instance.session_maker = session_maker

    return injector, engine
