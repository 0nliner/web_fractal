# mixins

---

## GenericRepo

```python
class UserRepo(GenericRepo):
    model = User                       # модель SQLAlchemy
    dm_class = UserDM                  # что выходит из репозитория
    session_maker: async_sessionmaker  # подставит archtool либо задайте руками
```

Единица работы всегда именованным аргументом:

```python
await create(data: list[dict], *, uow) -> list[DM]
await get(*, uow, **filters) -> DM                     # NotExist / MultipleFound
await get_or_none(*, uow, **filters) -> DM | None
await filter(selection: FilterBase, pag: Pagination, *, uow, eager_load: list[str] = []) -> list[DM]
await update(selection: FilterBase, payload: dict, *, uow) -> int
await delete(*, uow, **filters) -> int
await count(selection: FilterBase, *, uow) -> int
```

`eager_load` принимает имена связей и разворачивает их в `selectinload` — так
списочная ручка перестаёт делать N+1 запросов.

`update` и `delete` возвращают число затронутых строк.

---

## GenericService

```python
class UserService(GenericService):
    repo: UserRepo
```

Делегирует все методы репозитория и добавляет два хука:

```python
await before_create(data: list[dict]) -> list[dict]
await after_create(objects: list) -> list
```

---

## Исключения

| | |
|---|---|
| `NotExist` | `get` ничего не нашёл |
| `MultipleFound` | `get` нашёл больше одной строки |

Оба — обычные исключения из `web_fractal.mixins`. Превращайте их в HTTP-коды в
контроллере, тогда репозиторий останется пригодным и за не-HTTP транспортом.
