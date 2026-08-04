from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from web_fractal.db import Base, Dated


class Card(Base, Dated):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)

    # SM-2 spaced repetition fields
    interval: Mapped[int] = mapped_column(default=1)        # days until next review
    repetitions: Mapped[int] = mapped_column(default=0)     # successful review count
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    due_date: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)
