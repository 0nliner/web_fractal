"""
Test fixtures — archtool DI style.

Each test gets a fresh in-memory SQLite database.  build_injector() is
called with a test session_maker; archtool wires the full DI graph
(repo → service → controller) exactly like production, then
initialize_controllers_api() mounts routes on a fresh FastAPI app.

build_injector() calls import_all_models() internally, which registers
all ORM models with Base.metadata.  create_all() must therefore run
AFTER build_injector(), not before — hence the single merged fixture.

No app.dependency_overrides, no mocking — just a real SQLite session.
"""
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from web_fractal.building_utils import initialize_controllers_api
from web_fractal.db import Base

from app.archtool_conf.bundle import build_injector

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(TEST_DB, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    # build_injector calls import_all_models, which registers all ORM models
    # with Base.metadata.  create_all must come after.
    injector, _ = build_injector(session_maker=session_maker)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI()
    initialize_controllers_api(injector, app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    await engine.dispose()
