from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CardDM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    front: str
    back: str
    interval: int
    repetitions: int
    ease_factor: float
    due_date: Optional[datetime]


class CreateCardDTO(BaseModel):
    deck_id: int
    front: str
    back: str


class UpdateCardDTO(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None


class ReviewGradeDTO(BaseModel):
    grade: int = Field(..., ge=0, le=5, description="SM-2 grade: 0=blackout, 5=perfect recall")
