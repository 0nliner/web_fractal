# HTTP-контроллеры

Нужна экстра `fastapi`.

## Ручная регистрация

```python
from fastapi import APIRouter
from web_fractal.http.interfaces import HttpControllerABC

class UserController(HttpControllerABC):
    router = APIRouter(prefix="/users", tags=["users"])

    def init_http_routes(self) -> None:
        self.reg_route(self.create_user, methods=["POST"])
        self.reg_route(self.find_user, methods=["GET"], path="/{pk}")
```

`reg_route(method, methods=[...], path=None)` без `path` выводит путь из имени
метода и ставит `operation_id` равным имени метода — по нему называют функции
сгенерированные клиенты.

Каждый экземпляр получает свою копию роутера, поэтому повторная сборка в тестах
не копит дубликаты маршрутов на классовом атрибуте.

## Маршруты из имён методов

`AutoHttpController` выводит и глагол, и путь:

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

| Префикс | Метод и путь |
|---|---|
| `create_*`, `add_*`, `insert_*` | `POST /` |
| `get_*`, `retrieve_*`, `fetch_*`, `read_*` | `GET /{параметры пути}` |
| `filter_*`, `list_*`, `search_*` | `GET /` |
| `update_*`, `patch_*`, `edit_*` | `PATCH /{параметры пути}` |
| `delete_*`, `remove_*` | `DELETE /{параметры пути}` |

Скалярные параметры (`int`, `str`, `float`, `bool`, `UUID`) становятся
сегментами пути, остальное остаётся телом или зависимостью. Чтобы забрать
контроль целиком, определите `init_http_routes()` сами.

## Монтирование

```python
from web_fractal.building_utils import import_all_models, initialize_controllers_api

import_all_models(Base=Base)          # полная metadata до разводки
injector.inject()
initialize_controllers_api(injector=injector, app=app)
```

!!! warning "archtool 2.x"
    `initialize_controllers_api` читает реестр зависимостей инжектора. Если ваш
    archtool старше переименования `_dependencies` в `dependencies`, функция
    найдёт ноль контроллеров, и приложение поднимется **молча** с пустым
    роутером. Безопасная альтернатива — смонтировать контроллеры своим циклом
    по инжектору.
