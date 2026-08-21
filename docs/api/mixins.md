# mixins

---

## GenericRepo

```python
class UserRepo(GenericRepo):
    model = User                       # SQLAlchemy model
    dm_class = UserDM                  # what leaves the repository
    session_maker: async_sessionmaker  # supplied by archtool, or set by hand
```

The unit of work is always a keyword argument:

```python
await create(data: list[dict], *, uow) -> list[DM]
await get(*, uow, **filters) -> DM                     # NotExist / MultipleFound
await get_or_none(*, uow, **filters) -> DM | None
await filter(selection: FilterBase, pag: Pagination, *, uow, eager_load: list[str] = []) -> list[DM]
await update(selection: FilterBase, payload: dict, *, uow) -> int
await delete(*, uow, **filters) -> int
await count(selection: FilterBase, *, uow) -> int
```

`eager_load` takes relation names and turns them into `selectinload`, which is
how you avoid the N+1 that a list endpoint otherwise produces.

`update` and `delete` return the number of affected rows.

---

## GenericService

```python
class UserService(GenericService):
    repo: UserRepo
```

Delegates every repository method and adds two hooks:

```python
await before_create(data: list[dict]) -> list[dict]
await after_create(objects: list) -> list
```

---

## Exceptions

| | |
|---|---|
| `NotExist` | `get` matched nothing |
| `MultipleFound` | `get` matched more than one row |

Both are plain exceptions from `web_fractal.mixins` — map them to HTTP codes in
the controller, so the repository stays usable behind a non-HTTP transport.
