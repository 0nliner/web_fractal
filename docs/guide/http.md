# HTTP controllers

Requires the `fastapi` extra.

## Manual registration

```python
from fastapi import APIRouter
from web_fractal.http.interfaces import HttpControllerABC

class UserController(HttpControllerABC):
    router = APIRouter(prefix="/users", tags=["users"])

    def init_http_routes(self) -> None:
        self.reg_route(self.create_user, methods=["POST"])
        self.reg_route(self.find_user, methods=["GET"], path="/{pk}")
```

`reg_route(method, methods=[...], path=None)` derives the path from the method
name when `path` is omitted, and sets `operation_id` to the method name — which
is what generated clients use for naming.

Each instance gets a fresh router copy, so repeated assembly in tests does not
accumulate duplicate routes on the class attribute.

## Routes from method names

`AutoHttpController` derives the verb and path from the name:

```python
from web_fractal.http.auto_controller import AutoHttpController

class UserController(AutoHttpController):
    router = APIRouter(prefix="/users", tags=["users"])

    async def create_user(self, payload: CreateUserDTO) -> UserDM: ...
    async def get_user(self, pk: int) -> UserDM: ...
    async def filter_users(self, f: UserFilter) -> list[UserDM]: ...
    async def update_user(self, pk: int, payload: UpdateUserDTO) -> UserDM: ...
    async def delete_user(self, pk: int) -> None: ...
```

| Prefix | Method and path |
|---|---|
| `create_*`, `add_*`, `insert_*` | `POST /` |
| `get_*`, `retrieve_*`, `fetch_*`, `read_*` | `GET /{path params}` |
| `filter_*`, `list_*`, `search_*` | `GET /` |
| `update_*`, `patch_*`, `edit_*` | `PATCH /{path params}` |
| `delete_*`, `remove_*` | `DELETE /{path params}` |

Scalar parameters (`int`, `str`, `float`, `bool`, `UUID`) become path segments;
everything else stays a body or dependency. Define `init_http_routes()` yourself
to take back full control.

## Mounting

```python
from web_fractal.building_utils import import_all_models, initialize_controllers_api

import_all_models(Base=Base)          # complete metadata before assembly
injector.inject()
initialize_controllers_api(injector=injector, app=app)
```

!!! warning "archtool 2.x"
    `initialize_controllers_api` reads the injector's dependency registry. If
    your archtool predates the rename of `_dependencies` to `dependencies`, it
    finds zero controllers and the app starts **silently** with an empty router.
    Mounting the controllers with your own loop over the injector is a safe
    alternative.
