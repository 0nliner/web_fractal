"""
Phase 5 tests: AutoHttpController — route auto-registration from naming conventions.
"""
import inspect

import pytest
from fastapi import APIRouter
from pydantic import BaseModel

from web_fractal.http.auto_controller import (
    AutoHttpController,
    _build_path,
    _infer_http_method,
    _infer_path_params,
)


# ---------------------------------------------------------------------------
# _infer_http_method
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("create_user", "POST"),
    ("add_item", "POST"),
    ("insert_record", "POST"),
    ("get_user", "GET"),
    ("retrieve_item", "GET"),
    ("fetch_data", "GET"),
    ("filter_users", "GET"),
    ("list_orders", "GET"),
    ("search_products", "GET"),
    ("update_user", "PATCH"),
    ("patch_item", "PATCH"),
    ("edit_record", "PATCH"),
    ("delete_user", "DELETE"),
    ("remove_item", "DELETE"),
    ("some_other_name", "GET"),  # default
])
def test_infer_http_method(name, expected):
    assert _infer_http_method(name) == expected


# ---------------------------------------------------------------------------
# _infer_path_params
# ---------------------------------------------------------------------------

def test_infer_path_params_int():
    def fn(self, user_id: int): ...
    sig = inspect.signature(fn)
    assert _infer_path_params(sig) == ["user_id"]


def test_infer_path_params_str():
    def fn(self, slug: str): ...
    sig = inspect.signature(fn)
    assert _infer_path_params(sig) == ["slug"]


def test_infer_path_params_skips_self():
    def fn(self): ...
    assert _infer_path_params(inspect.signature(fn)) == []


def test_infer_path_params_skips_uow():
    def fn(self, uow): ...
    assert _infer_path_params(inspect.signature(fn)) == []


def test_infer_path_params_skips_pydantic_body():
    class MyDTO(BaseModel):
        name: str

    def fn(self, data: MyDTO): ...
    assert _infer_path_params(inspect.signature(fn)) == []


def test_infer_path_params_multiple():
    def fn(self, org_id: int, user_id: int): ...
    sig = inspect.signature(fn)
    assert _infer_path_params(sig) == ["org_id", "user_id"]


def test_infer_path_params_no_annotation_skipped():
    def fn(self, x): ...
    assert _infer_path_params(inspect.signature(fn)) == []


# ---------------------------------------------------------------------------
# _build_path
# ---------------------------------------------------------------------------

def test_build_path_empty():
    assert _build_path([]) == "/"


def test_build_path_single():
    assert _build_path(["user_id"]) == "/{user_id}"


def test_build_path_multiple():
    assert _build_path(["org_id", "user_id"]) == "/{org_id}/{user_id}"


# ---------------------------------------------------------------------------
# AutoHttpController route registration
# ---------------------------------------------------------------------------

class UserDM(BaseModel):
    id: int
    name: str


class UsersController(AutoHttpController):
    router = APIRouter(prefix="/users")

    async def create_user(self, name: str) -> UserDM:
        ...

    async def get_user(self, user_id: int) -> UserDM:
        ...

    async def filter_users(self) -> list[UserDM]:
        ...

    async def update_user(self, user_id: int) -> UserDM:
        ...

    async def delete_user(self, user_id: int) -> None:
        ...


def _get_routes(controller: AutoHttpController) -> dict:
    """Map operation_id → (path, methods) from registered routes."""
    return {
        r.operation_id: (r.path, r.methods)
        for r in controller.router.routes
    }


@pytest.fixture
def users_ctrl():
    ctrl = UsersController()
    ctrl.init_http_routes()
    return ctrl


def test_create_route_is_post(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "create_user" in routes
    assert "POST" in routes["create_user"][1]


def test_get_route_is_get_with_path_param(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "get_user" in routes
    assert "GET" in routes["get_user"][1]
    assert "{user_id}" in routes["get_user"][0]


def test_filter_route_is_get_no_path_param(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "filter_users" in routes
    assert "GET" in routes["filter_users"][1]
    assert "{" not in routes["filter_users"][0]


def test_update_route_is_patch(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "update_user" in routes
    assert "PATCH" in routes["update_user"][1]


def test_delete_route_is_delete(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "delete_user" in routes
    assert "DELETE" in routes["delete_user"][1]


def test_private_methods_not_registered(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert all(not k.startswith("_") for k in routes)


def test_init_http_routes_not_registered(users_ctrl):
    routes = _get_routes(users_ctrl)
    assert "init_http_routes" not in routes


def test_manual_override_wins():
    """If init_http_routes is explicitly defined, auto-scan is bypassed."""
    registered = []

    class ManualController(AutoHttpController):
        router = APIRouter(prefix="/manual")

        def init_http_routes(self):
            registered.append("manual_called")

        async def create_something(self) -> None:
            ...

    ctrl = ManualController()
    ctrl.init_http_routes()
    assert registered == ["manual_called"]
    assert len(_get_routes(ctrl)) == 0


def test_controller_with_no_handlers():
    class EmptyController(AutoHttpController):
        router = APIRouter()

    ctrl = EmptyController()
    ctrl.init_http_routes()
    assert len(_get_routes(ctrl)) == 0
