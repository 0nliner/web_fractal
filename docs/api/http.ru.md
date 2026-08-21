# http

Нужна экстра `fastapi`.

---

## HttpControllerABC

`web_fractal.http.interfaces`

```python
class UserController(HttpControllerABC):
    router = APIRouter(prefix="/users", tags=["users"])

    def init_http_routes(self) -> None: ...
```

| Член | |
|---|---|
| `router` | классовый атрибут; каждый экземпляр получает свою копию, поэтому повторная сборка не копит дубликаты маршрутов |
| `init_http_routes()` | абстрактный: здесь регистрируются маршруты |
| `reg_route(method, **overrides)` | путь по умолчанию `/{имя метода}`, `operation_id` — имя метода |

`reg_route` передаёт переопределения прямо в `add_api_route`, поэтому `path`,
`methods`, `status_code`, `response_model` и прочее работают как в FastAPI.

---

## AutoHttpController

`web_fractal.http.auto_controller`

Выводит маршруты из имён методов, если `init_http_routes` не переопределён:

| Префикс | Метод и путь |
|---|---|
| `create_*`, `add_*`, `insert_*` | `POST /` |
| `get_*`, `retrieve_*`, `fetch_*`, `read_*` | `GET /{параметры пути}` |
| `filter_*`, `list_*`, `search_*` | `GET /` |
| `update_*`, `patch_*`, `edit_*` | `PATCH /{параметры пути}` |
| `delete_*`, `remove_*` | `DELETE /{параметры пути}` |

Скалярные параметры (`int`, `str`, `float`, `bool`, `UUID`) становятся
сегментами пути. `init_http_routes`, `reg_route`, `on_startup`, `on_shutdown`
эндпоинтами не считаются никогда.

---

## building_utils

```python
import_all_models(Base) -> list[DeclarativeBase]
```
Импортирует `models.py` каждого модуля из реестра модулей проекта, чтобы
`Base.metadata` была полной до сборки или автогенерации alembic.

```python
initialize_controllers_api(injector, app: FastAPI | None = None)
```
Вызывает `init_http_routes()` у каждого `HttpControllerABC` в инжекторе и
подключает его роутер; заодно запускает регистрацию CLI-контроллеров.

```python
filter_objects_of_type(injector, obj_type) -> list
```
Все экземпляры типа в инжекторе — кирпич, из которого сделаны две функции выше;
пригодится, если монтируете контроллеры сами.
