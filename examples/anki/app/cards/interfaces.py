from abc import abstractmethod
from typing import Any, Optional

from archtool.layers.default_layer_interfaces import ABCController, ABCRepo, ABCService

from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination

from .dtos import CardDM, CreateCardDTO, ReviewGradeDTO, UpdateCardDTO
from .filters import CardFilter


class CardRepoABC(ABCRepo):
    """CRUD repository contract for the Card model."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[CardDM]:
        """Bulk-insert cards and return their domain models."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> CardDM:
        """Return a single card matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[CardDM]:
        """Return a single card or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: CardFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[CardDM]:
        """Return a filtered, paginated list of cards."""

    @abstractmethod
    async def update(self, selection: CardFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all cards matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete cards matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: CardFilter, *, uow: UnitOfWork) -> int:
        """Return the number of cards matching selection."""


class CardServiceABC(ABCService):
    """Business-logic contract for the Card domain."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[CardDM]:
        """Create cards, invoking before_create / after_create hooks."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> CardDM:
        """Return a single card matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[CardDM]:
        """Return a single card or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: CardFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[CardDM]:
        """Return a filtered, paginated list of cards."""

    @abstractmethod
    async def update(self, selection: CardFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all cards matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete cards matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: CardFilter, *, uow: UnitOfWork) -> int:
        """Return the number of cards matching selection."""

    @abstractmethod
    async def review(self, card_id: int, grade: int, *, uow: UnitOfWork) -> CardDM:
        """Apply SM-2 scheduling to card_id with the given grade (0–5).

        grade < 3  → failed recall: reset interval=1, repetitions=0
        grade >= 3 → successful recall: increment repetitions, scale interval by ease_factor
        Returns the updated card.
        """


class CardsControllerABC(ABCController):
    """HTTP controller contract for the /cards resource."""

    @abstractmethod
    def init_http_routes(self) -> None:
        """Register all HTTP routes on self.router."""

    @abstractmethod
    async def create_card(self, data: CreateCardDTO) -> CardDM:
        """POST /cards/ — create a new card with default SM-2 values."""

    @abstractmethod
    async def get_card(self, card_id: int) -> CardDM:
        """GET /cards/{card_id} — retrieve a card by id. 404 if absent."""

    @abstractmethod
    async def filter_cards(
        self,
        deck_id__eq: Optional[int],
        due_before: Optional[str],
        order_by: Optional[str],
        page: Optional[int],
        size: Optional[int],
    ) -> list[CardDM]:
        """GET /cards/ — list cards; due_before filters by ISO-8601 datetime."""

    @abstractmethod
    async def update_card(self, card_id: int, data: UpdateCardDTO) -> CardDM:
        """PATCH /cards/{card_id} — partial update. 422 on empty body, 404 if absent."""

    @abstractmethod
    async def delete_card(self, card_id: int) -> None:
        """DELETE /cards/{card_id} — remove a card. 404 if absent."""

    @abstractmethod
    async def review_card(self, card_id: int, data: ReviewGradeDTO) -> CardDM:
        """POST /cards/{card_id}/review — apply SM-2 grade and return updated card."""
