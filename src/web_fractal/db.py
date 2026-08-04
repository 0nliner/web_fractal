from datetime import datetime, timezone, tzinfo
from enum import Enum
import hashlib
import json
import typing as t

from furl import furl
from sqlalchemy import TIMESTAMP, DateTime, create_engine, JSON
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, InstrumentedAttribute
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession, AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty

from web_fractal.dtos import Pagination
from web_fractal.utils import now, serialize
from web_fractal.types import Unset, UNSET

T = t.TypeVar('T')
R = t.TypeVar('R')

from typing_extensions import NotRequired
from typing import TypeVar


class BaseTypedDict(dict):
    """dict subclass with not_blank helper and serialize_model utility."""

    @property
    def not_blank(self) -> dict[str, t.Any]:
        return {key: value for key, value in self.items() if (value is not Unset) and (value is not UNSET)}

    def serialize_model(self, data: DeclarativeMeta) -> dict[str, t.Any]:
        data_as_dict = data.__dict__ if hasattr(data, "__dict__") else data
        for key, val in t.get_type_hints(type(self)).items():
            args = val.__args__[0] if hasattr(val, "__args__") else val
            if key in data_as_dict:
                data_as_dict[key] = serialize(args, data_as_dict[key])
        return data_as_dict


from sqlalchemy.ext.mutable import MutableDict

MutableJSONT = dict[str, t.Any]
ImmutableJSONT = [dict[str, t.Any]]

class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        MutableJSONT: MutableDict.as_mutable(JSON),
        datetime: TIMESTAMP(timezone=True)
    }


from typing import TypedDict

class UOFParams(TypedDict, total=False):
    uof: 'UnitOfWork'
    commit: bool
    return_orm: bool


from contextlib import asynccontextmanager
from enum import Enum
from sqlalchemy import asc, desc


def order_by_field(q: T, model: Base, field: str) -> T:
    is_asc = not field.startswith('-')
    field_name = field if not field.startswith('-') else field[1:]
    if is_asc:
        q = q.order_by(asc(field_name))
    else:
        q = q.order_by(desc(field_name))
    return q


class BaseRepo(t.Generic[T, R]):
    session_maker: async_sessionmaker
        
    def _to_dto(self, model: T, dto_class: t.Type[R]) -> t.Optional[R]:
        return serialize(dto_class, model) if model else None
        
    def _to_dto_list(self, models: list[T], dto_class: t.Type[R]) -> list[R]:
        return serialize(dto_class, models, as_list=True) if models else []

    @asynccontextmanager
    async def get_session(self, uof: 'UnitOfWork') -> t.AsyncGenerator[AsyncSession, None]:
        if uof.session:
            yield uof.session
        else:
            session = self.session_maker()
            try:
                yield session
            finally:
                await session.close()

    @asynccontextmanager
    async def in_session(self, uof: t.Optional['UnitOfWork'] = None) -> t.AsyncGenerator[AsyncSession, None]:
        if uof:
            yield uof.session
        else:
            session = self.session_maker()
            try:
                yield session
            finally:
                await session.close()

from typing import Optional 

class UnitOfWork:
    def __init__(self, session_maker):
        self.session_maker = session_maker
        self.session: t.Optional[AsyncSession] = None
        self.objects = []

    async def __aenter__(self):
        self.session = self.session_maker()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.close()
        
    async def commit(self, refresh: bool = False):
        if self.session:
            await self.session.commit()
        if refresh:
            for o in self.objects:
                await self.session.refresh(o)
        
    async def rollback(self):
        if self.session:
            await self.session.rollback()
            
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def register(self, objects: list, refresh: Optional[bool] = False, flush: bool=False):
        self.objects.extend(objects)
        self.session.add_all(objects)
        if flush:
            await self.session.flush(objects)
        if refresh:
            for obj in objects:
                await self.session.refresh(obj)

    def get_session(self) -> AsyncSession:
        if not self.session:
            raise RuntimeError("Session is not initialized. Use UnitOfWork as context manager.")
        return self.session


SELF_T = TypeVar("SELF_T")
ORIGINAL_DATA = TypeVar("ORIGINAL_DATA")


def get_no_db_engine(dsn):
    f = furl(dsn)
    db_name = f.path.segments[0]
    f.path.remove(db_name)  # Remove database name from DSN
    return create_engine(f.url, isolation_level="AUTOCOMMIT")


def get_db_name(dsn: str) -> str:
    f = furl(dsn)
    return f.path.segments[0]


class Dated:
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)



T = t.TypeVar("T")

def paginate(query: T, pag_info: Pagination) -> T:
    offset = (pag_info.page - 1) * pag_info.size
    paginated = query.offset(offset).limit(pag_info.size)
    return paginated


def get_now(tz: tzinfo = timezone.utc) -> datetime:
    return datetime.now(tz=tz)



async def init_db(Base: DeclarativeMeta,
                  db_uri: str,
                  engine: AsyncEngine,
                  drop_db: bool):
    dbschema = "public"
    async with engine.begin() as conn:
        from sqlalchemy.sql import text
        if drop_db:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.execute(text(f'set search_path={dbschema}'))
            await conn.run_sync(Base.metadata.create_all)


async def drop_db(Base: DeclarativeMeta, db_uri: str) ->  AsyncEngine:    
    engine = create_async_engine(db_uri, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    return engine


def get_json_hash(data: t.Any, hash_algorithm: str = 'sha256') -> str:
    """
    Вычисляет хэш JSON-совместимого объекта.
    
    Параметры:
        data: Любой JSON-сериализуемый объект (dict, list, str и т.д.)
        hash_algorithm: Алгоритм хеширования (sha256, md5, sha1 и т.д.)
    
    Возвращает:
        Строку с шестнадцатеричным представлением хэша
    """
    # Сериализуем в JSON с гарантированным порядком ключей
    json_str = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,  # Для одинакового порядка ключей
        indent=None,
        separators=(',', ':')
    )
    
    # Кодируем в байты (UTF-8) и вычисляем хэш
    hash_obj = hashlib.new(hash_algorithm)
    hash_obj.update(json_str.encode('utf-8'))
    
    return hash_obj.hexdigest()

from typing import Optional

def apply_filters(q: T, apply_to: t.Any, filters: dict, ignore: Optional[list[str]] = None) -> T:
    ignore = ignore if ignore else []
    return q.where(*list(getattr(apply_to, key).__eq__(val) for key, val in filters.items() if key not in ignore))


def get_enum_values(e: Enum) -> list:
    return [val.value for key, val in e.__members__.items()]

import sqlalchemy as sa
from archtool.utils import string_to_snake_case


def create_enum_column(enum: Enum) -> sa.Enum:
    enum_col_T = sa.Enum(*get_enum_values(enum), name=string_to_snake_case(enum.__name__), metadata=Base.metadata, create_constraint=True, validate_strings=True)
    return enum_col_T


ORM_OBJ_T = TypeVar("ORM_OBJ_T", bound=Base)

from typing import Any

async def copy_object(entity: ORM_OBJ_T, 
                      uof: UnitOfWork, 
                      use_same: Optional[dict[str, list[str]]] = None,
                      ignore: Optional[list[str]] = None,
                      flush: bool = True,
                      all_objects: Optional[list[Any]] = None,
                      **overrides) -> ORM_OBJ_T:
    """
    производит глубокое копирование объекта орм
    """
    if all_objects is None:
        all_objects = []

    async with uof.get_session() as session:
        mapper = type(entity)
        inspector = sa_inspect(mapper)
        new_entity = mapper()
        session.add(new_entity)
        all_objects.append(new_entity)

        # Копируем атрибуты
        for key, current_mapper_field in mapper.__dict__.items():
            if key.startswith('_'):
                continue

            if ignore and key in ignore:
                continue

            inspectable_field = inspector.attrs.get(key)

            if current_mapper_field and isinstance(inspectable_field, RelationshipProperty)\
               and getattr(inspectable_field, "secondary", None) is not None:
                children_objects_original = await (getattr(entity.awaitable_attrs, key))
                children_copy_objects = await (getattr(new_entity.awaitable_attrs, key))
                for child in children_objects_original:
                    child_copy = await copy_object(child, uof, ignore=[inspectable_field.back_populates], flush=False, all_objects=all_objects)
                    children_copy_objects.append(child_copy)
                continue

            value = entity.__dict__[key]

            if current_mapper_field and\
               isinstance(current_mapper_field, InstrumentedAttribute)\
               and hasattr(current_mapper_field, "primary_key")\
               and current_mapper_field.primary_key:
                # пропускаем первичные ключи
                continue
            
            # if isinstance(value, list):  # One-to-Many
            #     new_children = []
            #     for child in value:
            #         new_child = await copy_object(child, uof)
            #         new_children.append(new_child)
            #     setattr(new_entity, key, new_children)
            elif hasattr(value, '__mapper__'):  # Many-to-One
                continue  # Не копируем "родителей"
            else:
                setattr(new_entity, key, value)
        
        # Применяем переопределения
        for key, value in overrides.items():
            setattr(new_entity, key, value)

        if flush:
            await session.flush([new_entity])
            # await session.refresh(new_entity)  
        return new_entity

