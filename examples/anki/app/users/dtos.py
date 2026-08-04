from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserDM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool


class CreateUserDTO(BaseModel):
    username: str
    email: str
    role: str = "student"


class UpdateUserDTO(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
