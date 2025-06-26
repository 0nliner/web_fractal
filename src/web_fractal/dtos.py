import uuid
from pydantic import BaseModel, Field
from enum import Enum

from pydantic import ConfigDict
from web_fractal.types import UNSET, Unset


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True,
                              from_attributes=True,
                              allow_population_by_field_name=True)

    @property
    def not_blank(self):
        return {key: value for key, value in vars(self).items() if (value is not Unset) and (value is not UNSET) }


class Pagination(Base):
    page: int = 1
    size: int = 40


class StatusEnum(Enum):
    error = "error"
    info = "info"
    success = "success"


class MessageDTO(Base):
    model_config = ConfigDict(use_enum_values=True)

    status: StatusEnum
    text: str
    id: uuid.UUID = Field(default_factory=uuid.uuid4)


class Context(Base):
    """
    Объект контекста будет формироваться
    в middleware и передаваться в методы 
    вьюх и сервисов
    """
    session_id: str


class DictWrapper(dict):
    def to_dict(self):
        return self
    

# from typing import TypedDict

# class TypedDictWithDefaultsMeta(type(TypedDict)):  # type: ignore
#     def __call__(cls, *args, **kwargs):
#         defaults = {}
#         """all defaults"""
#         keys = []
#         """all possible keys"""

#         # get defaults and keys info
#         anno = getattr(cls, '__annotations__', None)
#         if anno is not None:
#             keys = list(anno.keys())
#             if keys:
#                 defaults.update({attr: getattr(cls, attr) for attr in keys if hasattr(cls, attr)})

#         args_kw = {}
#         if args:  # convert args to kwargs
#             assert len(keys) >= len(args), f"found {len(args) - len(keys)} excess args"
#             args_kw = {k: v for k, v in zip(keys, args)}

#         if kwargs:
#             if args_kw:  # check no args-kwargs intersection
#                 assert not set(args_kw.keys()).intersection(kwargs.keys())
#             args_kw.update(kwargs)

#         defaults.update(args_kw)
#         _cur_k = set(defaults.keys())

#         keys = set(keys)
#         diff = keys - _cur_k
#         if diff:
#             raise ValueError(f"some required keys not found: {diff}")
#         diff = _cur_k - keys
#         if diff:
#             raise ValueError(f"excess keys found: {diff}")

#         return super().__call__(**defaults)



# class TypedDictWithDefaults(TypedDictWithDefaultsMeta, metaclass=TypedDictWithDefaultsMeta):
#     pass


# example
# class A(TypedDictWithDefaults):
#     a: int 
#     b: int = 2
# 
# print(A(1))  # {'b': 2, 'a': 1}
# print(A(a=3, b=4))  # {'b': 4, 'a': 3}