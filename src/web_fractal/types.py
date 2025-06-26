import datetime
from typing import Literal, TypeVar, Optional, Union, Any
from pydantic import BaseModel
from pydantic_core import core_schema


class Unset:
    @classmethod
    def __bool__(self):
        return False

    def __bool__(self) -> Literal[False]:
        return False

    def _validate(cls, value: Any) -> "Unset":
        # Любые нужные проверки:
        if not isinstance(value, cls):
            raise ValueError("Value must be an instance of Unset")
        return value

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        # Используем handler.generate_schema для предотвращения рекурсии
        return handler.generate_schema(None)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: core_schema.CoreSchema, handler: Any) -> dict:
        # В JSON будем отображать как null (либо можно вернуть другое значение)
        return {"type": "null"}


UNSET: Unset = Unset()


T = TypeVar("T")

DTOField = Union[T, UNSET]
OneOrMultuple = Union[T, list[T]]

DATE_RANGE_T = tuple[datetime.datetime, datetime.datetime]
TIME_RANGE_T = tuple[datetime.time, datetime.time]
