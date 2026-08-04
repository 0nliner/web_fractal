"""
ASGI entry-point.

Startup sequence:
  1. build_injector() creates the DependencyInjector, calls import_all_models(),
     wires the full DI graph, and sets session_maker on all repos + controllers.
  2. initialize_controllers_api() calls init_http_routes() on every
     HttpControllerABC and mounts its router on the FastAPI app.
  3. lifespan() creates DB tables on first startup, disposes engine on shutdown.

Run:
  uvicorn app.entrypoints.asgi:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.archtool_conf.bundle import build_injector
from app.config import DATABASE_URL
from web_fractal.building_utils import initialize_controllers_api
from web_fractal.db import Base


def create_app() -> FastAPI:
    injector, engine = build_injector(DATABASE_URL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(
        title="Anki Clone",
        description="web_fractal example — FilterBase DSL, ABAC, AutoHttpController, no FastAPI DI for services",
        version="0.1.0",
        lifespan=lifespan,
    )
    initialize_controllers_api(injector, app)
    return app


app = create_app()
