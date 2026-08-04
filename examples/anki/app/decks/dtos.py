from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeckDM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: Optional[str]
    is_public: bool


class CreateDeckDTO(BaseModel):
    owner_id: int
    title: str
    description: Optional[str] = None
    is_public: bool = False


class UpdateDeckDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
