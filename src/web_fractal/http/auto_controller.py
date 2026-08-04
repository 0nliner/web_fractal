"""
Phase 5: AutoHttpController — automatic route registration from method naming conventions.

create_* → POST /
get_* / retrieve_* / fetch_* / read_* → GET /{path_params}
filter_* / list_* / search_* → GET /
update_* / patch_* / edit_* → PATCH /{path_params}
delete_* / remove_* → DELETE /{path_params}

Users can override init_http_routes() for full manual control.
"""
import asyncio
import inspect
import uuid
from typing import Any, get_type_hints

from fastapi import APIRouter

from web_fractal.http.interfaces import HttpControllerABC

_SCALAR_TYPES = (int, str, float, bool, uuid.UUID)

_SKIP_METHODS = frozenset({"init_http_routes", "reg_route", "on_startup", "on_shutdown"})

_NAME_TO_HTTP: list[tuple[str, str]] = [
    ("create", "POST"),
    ("add", "POST"),
    ("insert", "POST"),
    ("get", "GET"),
    ("retrieve", "GET"),
    ("fetch", "GET"),
    ("read", "GET"),
    ("filter", "GET"),
    ("list", "GET"),
    ("search", "GET"),
    ("update", "PATCH"),
    ("patch", "PATCH"),
    ("edit", "PATCH"),
    ("delete", "DELETE"),
    ("remove", "DELETE"),
]


def _infer_http_method(name: str) -> str:
    for prefix, method in _NAME_TO_HTTP:
        if name.startswith(prefix):
            return method
    return "GET"


def _infer_path_params(sig: inspect.Signature) -> list[str]:
    path_params = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "uow", "session", "request", "background_tasks"):
            continue
        # Params with defaults are query/body params, not path params
        if param.default is not inspect.Parameter.empty:
            continue
        ann = param.annotation
        if ann is inspect.Parameter.empty:
            continue
        origin = getattr(ann, "__origin__", None)
        if origin is not None:
            continue
        try:
            from pydantic import BaseModel
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                continue
        except ImportError:
            pass
        try:
            from web_fractal.filters import FilterBase
            if isinstance(ann, type) and issubclass(ann, FilterBase):
                continue
        except ImportError:
            pass
        if isinstance(ann, type) and issubclass(ann, _SCALAR_TYPES):
            path_params.append(pname)
    return path_params


def _build_path(path_params: list[str]) -> str:
    if not path_params:
        return "/"
    return "/" + "/".join(f"{{{p}}}" for p in path_params)


class AutoHttpController(HttpControllerABC):
    """
    HttpControllerABC subclass that auto-registers routes from method naming.

    class UsersController(AutoHttpController):
        router = APIRouter(prefix="/users")

        async def create_user(self, data: CreateUserDTO) -> UserDM: ...
        async def get_user(self, user_id: int) -> UserDM: ...
        async def filter_users(self, filter: UserFilterDep) -> list[UserDM]: ...
        async def update_user(self, user_id: int, data: UpdateUserDTO) -> UserDM: ...
        async def delete_user(self, user_id: int) -> None: ...
    """

    def init_http_routes(self) -> None:
        for name in dir(self.__class__):
            if name.startswith("_") or name in _SKIP_METHODS:
                continue
            method = getattr(self.__class__, name, None)
            if method is None or not asyncio.iscoroutinefunction(method):
                continue

            http_method = _infer_http_method(name)
            sig = inspect.signature(method)
            path_params = _infer_path_params(sig)
            path = _build_path(path_params)

            try:
                hints = get_type_hints(method)
            except Exception:
                hints = {}
            return_type = hints.get("return")
            response_model = (
                None if return_type in (None, type(None)) else return_type
            )

            bound = getattr(self, name)
            self.router.add_api_route(
                path,
                bound,
                methods=[http_method],
                response_model=response_model,
                operation_id=name,
            )
