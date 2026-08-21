# http

Requires the `fastapi` extra.

---

## HttpControllerABC

`web_fractal.http.interfaces`

```python
class UserController(HttpControllerABC):
    router = APIRouter(prefix="/users", tags=["users"])

    def init_http_routes(self) -> None: ...
```

| Member | |
|---|---|
| `router` | class attribute; each instance receives a fresh copy, so repeated assembly does not accumulate duplicate routes |
| `init_http_routes()` | abstract: register the routes here |
| `reg_route(method, **overrides)` | path defaults to `/{method name}`, `operation_id` to the method name |

`reg_route` passes overrides straight to `add_api_route`, so `path`,
`methods`, `status_code`, `response_model` and the rest behave as in FastAPI.

---

## AutoHttpController

`web_fractal.http.auto_controller`

Derives routes from method names when `init_http_routes` is not overridden:

| Prefix | Method and path |
|---|---|
| `create_*`, `add_*`, `insert_*` | `POST /` |
| `get_*`, `retrieve_*`, `fetch_*`, `read_*` | `GET /{path params}` |
| `filter_*`, `list_*`, `search_*` | `GET /` |
| `update_*`, `patch_*`, `edit_*` | `PATCH /{path params}` |
| `delete_*`, `remove_*` | `DELETE /{path params}` |

Scalar parameters (`int`, `str`, `float`, `bool`, `UUID`) become path segments.
`init_http_routes`, `reg_route`, `on_startup`, `on_shutdown` are never treated
as endpoints.

---

## building_utils

```python
import_all_models(Base) -> list[DeclarativeBase]
```
Imports `models.py` of every module listed in the project's module registry, so
`Base.metadata` is complete before assembly or an Alembic autogenerate.

```python
initialize_controllers_api(injector, app: FastAPI | None = None)
```
Calls `init_http_routes()` on every `HttpControllerABC` found in the injector and
includes its router; also triggers CLI controller registration.

```python
filter_objects_of_type(injector, obj_type) -> list
```
Every instance of a type in the injector — the building block of the two
functions above, useful when mounting controllers yourself.
