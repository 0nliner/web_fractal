# Быстрый старт

Списочная ручка с типизированной фильтрацией, сортировкой и пагинацией —
целиком.

## 1. Модель и DM

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

## 2. Фильтр

```python
from web_fractal.filters import FilterBase, FilterField

class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
```

## 3. Репозиторий

```python
from web_fractal.mixins import GenericRepo

class UserRepo(GenericRepo):
    model = User
    dm_class = UserDM
    session_maker: async_sessionmaker   # подставит archtool либо задайте руками
```

## 4. Ручка

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

## Что получилось

```
GET /users?name__ilike=иван&age__gte=30&order_by=-age&page=2&size=20
```

* каждый параметр явно виден в Swagger — вместе с операторами, которые
  допускает тип поля;
* `name__gte` игнорируется, а не падает: неизвестный оператор не превращается
  в 500;
* на выходе `list[UserDM]`, а не ORM-объекты.

## Дальше

* [DSL фильтров](filters.md) — операторы, enum-ы, сортировка
* [Права доступа (ABAC)](security.md) — как сузить тот же фильтр правами
* [CRUD-миксины](mixins.md) — остальное из `GenericRepo`
