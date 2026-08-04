"""
CardService — wraps GenericService with the SM-2 spaced repetition algorithm.

SM-2 summary:
  grade < 3  → reset to interval=1, repetitions=0 (failed recall)
  grade >= 3 → increment repetitions, multiply interval by ease_factor
  ease_factor adjusts based on how well the card was recalled.
"""
from datetime import UTC, datetime, timedelta

from web_fractal.db import UnitOfWork
from web_fractal.mixins import GenericService

from .dtos import CardDM
from .filters import CardFilter
from .interfaces import CardRepoABC, CardServiceABC


def _sm2(card: CardDM, grade: int) -> dict:
    if grade < 3:
        interval = 1
        repetitions = 0
    else:
        if card.repetitions == 0:
            interval = 1
        elif card.repetitions == 1:
            interval = 6
        else:
            interval = round(card.interval * card.ease_factor)
        repetitions = card.repetitions + 1

    ease = max(1.3, card.ease_factor + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    return {
        "interval": interval,
        "repetitions": repetitions,
        "ease_factor": round(ease, 4),
        "due_date": datetime.now(UTC) + timedelta(days=interval),
    }


class CardService(GenericService, CardServiceABC):
    repo: CardRepoABC  # archtool injects CardRepo instance

    async def review(self, card_id: int, grade: int, *, uow: UnitOfWork) -> CardDM:
        card = await self.repo.get(uow=uow, id=card_id)
        payload = _sm2(card, grade)
        selection = CardFilter(id__eq=card_id)
        await self.repo.update(selection, payload, uow=uow)
        return await self.repo.get(uow=uow, id=card_id)
