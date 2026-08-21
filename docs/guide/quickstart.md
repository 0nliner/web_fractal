# Quickstart

A list endpoint with typed filtering, ordering and pagination — end to end.

## 1. Model and DM

```python
from sqlalchemy.orm import Mapped, mapped_column
from web_fractal.db import Base
from web_fractal.dtos import Base as DTOBase

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]

class UserDM(DTOBase):
    id: int
    name: str
    age: int
```

## 2. Filter

```python
from web_fractal.filters import FilterBase, FilterField

class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
```

## 3. Repository

```python
from web_fractal.mixins import GenericRepo

class UserRepo(GenericRepo):
    model = User
    dm_class = UserDM
    session_maker: async_sessionmaker   # injected by archtool, or set by hand
```

## 4. Endpoint

```python
from typing import Annotated
from fastapi import Depends
from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination

UserFilterDep = UserFilter.as_fastapi_dep()

@router.get("/users")
async def list_users(
    f: Annotated[UserFilter, Depends(UserFilterDep)],
    pag: Pagination = Depends(),
) -> list[UserDM]:
    async with UnitOfWork(session_maker) as uow:
        return await repo.filter(f, pag, uow=uow)
```

## What you get

```
GET /users?name__ilike=иван&age__gte=30&order_by=-age&page=2&size=20
```

* every parameter is explicit in Swagger, with the operators the field type
  allows;
* `name__gte` is ignored instead of raising — an unknown operator never becomes
  a 500;
* the result is `list[UserDM]`, not ORM objects.

## Next

* [Filters DSL](filters.md) — operators, enums, ordering
* [Security (ABAC)](security.md) — narrowing the same filter by permissions
* [CRUD mixins](mixins.md) — the rest of `GenericRepo`
