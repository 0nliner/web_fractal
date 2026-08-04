import uuid
from pydantic import BaseModel, Field
from enum import Enum

from pydantic import ConfigDict
from web_fractal.types import UNSET, Unset


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True,
                              from_attributes=True,
                              populate_by_name=True)

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