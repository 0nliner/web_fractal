"""
Phase 4: CRUD Mixins — GenericRepo and GenericService.

Usage:
    class UserRepo(GenericRepo):
        model = User
        dm_class = UserDM
        session_maker: async_sessionmaker  # injected by archtool

    class UserService(GenericService):
        repo: UserRepo  # injected by archtool
"""
import typing as t
from typing import Any, ClassVar, Generic, Optional, Type, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import selectinload

from web_fractal.db import UnitOfWork, paginate
from web_fractal.dtos import Pagination
from web_fractal.filters import FilterBase, _build_where_conditions

ModelT = TypeVar("ModelT")
DMT = TypeVar("DMT")


class NotExist(Exception):
    """Raised when a required record is not found."""


class MultipleFound(Exception):
    """Raised when one record was expected but multiple exist."""


class GenericRepo(Generic[ModelT, DMT]):
    """
    Base CRUD repository.

    Declare on the subclass:
        model: ClassVar[Type[ModelT]]
        dm_class: ClassVar[Type[DMT]]        session_maker: async_sessionmaker  # injected by archtool
    """

    model: ClassVar[Type]
    dm_class: ClassVar[Type]
    MAX_BULK_CREATE: ClassVar[int] = 1000

    def _to_dm(self, obj: Any) -> Any:
        return self.dm_class.model_validate(obj)

    def _to_dm_list(self, objects: list) -> list:
        return [self._to_dm(obj) for obj in objects]

    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list:
        objects = [self.model(**item) for item in data[: self.MAX_BULK_CREATE]]
        await uow.register(objects, flush=True)
        return self._to_dm_list(objects)

    async def get(self, *, uow: UnitOfWork, **filters) -> Any:
        q = select(self.model)
        for key, val in filters.items():
            col = getattr(self.model, key, None)
            if col is not None:
                q = q.where(col == val)
        result = (await uow.session.execute(q)).scalars().first()
        if result is None:
            raise NotExist(f"{self.model.__name__} not found: {filters}")
        return self._to_dm(result)

    async def get_or_none(self, *, uow: UnitOfWork, **filters) -> Optional[Any]:
        try:
            return await self.get(uow=uow, **filters)
        except NotExist:
            return None

    async def filter(
        self,
        selection: FilterBase,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list:
        from web_fractal.filters import apply_selection

        q = select(self.model)
        for rel_name in eager_load:
            rel = getattr(self.model, rel_name, None)
            if rel is not None:
                q = q.options(selectinload(rel))
        q = apply_selection(q, self.model, selection)
        q = paginate(q, pag)
        result = (await uow.session.execute(q)).scalars().all()
        return self._to_dm_list(result)

    async def update(self, selection: FilterBase, payload: dict, *, uow: UnitOfWork) -> int:
        conditions = _build_where_conditions(self.model, selection)
        q = sa_update(self.model).values(**payload)
        if conditions:
            q = q.where(*conditions)
        result = await uow.session.execute(q)
        return result.rowcount

    async def delete(self, *, uow: UnitOfWork, **filters) -> int:
        q = sa_delete(self.model)
        for key, val in filters.items():
            col = getattr(self.model, key, None)
            if col is not None:
                q = q.where(col == val)
        result = await uow.session.execute(q)
        return result.rowcount

    async def count(self, selection: FilterBase, *, uow: UnitOfWork) -> int:
        from web_fractal.filters import apply_selection

        q = apply_selection(select(func.count()).select_from(self.model), self.model, selection)
        return (await uow.session.execute(q)).scalar_one()


class GenericService(Generic[ModelT, DMT]):
    """
    Base service — delegates to GenericRepo and exposes override hooks.

    Declare on the subclass:
        repo: ConcreteRepo  # injected by archtool
    """

    async def before_create(self, data: list[dict]) -> list[dict]:
        return data

    async def after_create(self, objects: list) -> list:
        return objects

    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list:
        data = await self.before_create(data)
        result = await self.repo.create(data, uow=uow)
        return await self.after_create(result)

    async def get(self, *, uow: UnitOfWork, **filters) -> Any:
        return await self.repo.get(uow=uow, **filters)

    async def get_or_none(self, *, uow: UnitOfWork, **filters) -> Optional[Any]:
        return await self.repo.get_or_none(uow=uow, **filters)

    async def filter(
        self,
        selection: FilterBase,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list:
        return await self.repo.filter(selection, pag, uow=uow, eager_load=eager_load)

    async def update(self, selection: FilterBase, payload: dict, *, uow: UnitOfWork) -> int:
        return await self.repo.update(selection, payload, uow=uow)

    async def delete(self, *, uow: UnitOfWork, **filters) -> int:
        return await self.repo.delete(uow=uow, **filters)

    async def count(self, selection: FilterBase, *, uow: UnitOfWork) -> int:
        return await self.repo.count(selection, uow=uow)
