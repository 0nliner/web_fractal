from abc import abstractmethod
from typing import Any, Optional

from archtool.layers.default_layer_interfaces import ABCController, ABCRepo, ABCService

from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination

from .dtos import CreateDeckDTO, DeckDM, UpdateDeckDTO
from .filters import DeckFilter


class DeckRepoABC(ABCRepo):
    """CRUD repository contract for the Deck model."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[DeckDM]:
        """Bulk-insert decks and return their domain models."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> DeckDM:
        """Return a single deck matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[DeckDM]:
        """Return a single deck or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: DeckFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[DeckDM]:
        """Return a filtered, paginated list of decks."""

    @abstractmethod
    async def update(self, selection: DeckFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all decks matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete decks matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: DeckFilter, *, uow: UnitOfWork) -> int:
        """Return the number of decks matching selection."""


class DeckServiceABC(ABCService):
    """Business-logic contract for the Deck domain."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[DeckDM]:
        """Create decks, invoking before_create / after_create hooks."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> DeckDM:
        """Return a single deck matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[DeckDM]:
        """Return a single deck or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: DeckFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[DeckDM]:
        """Return a filtered, paginated list of decks."""

    @abstractmethod
    async def update(self, selection: DeckFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all decks matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete decks matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: DeckFilter, *, uow: UnitOfWork) -> int:
        """Return the number of decks matching selection."""


class DecksControllerABC(ABCController):
    """HTTP controller contract for the /decks resource."""

    @abstractmethod
    def init_http_routes(self) -> None:
        """Register all HTTP routes on self.router."""

    @abstractmethod
    async def create_deck(self, data: CreateDeckDTO) -> DeckDM:
        """POST /decks/ — create a new deck."""

    @abstractmethod
    async def get_deck(self, deck_id: int) -> DeckDM:
        """GET /decks/{deck_id} — retrieve a deck by id. 404 if absent."""

    @abstractmethod
    async def filter_decks(
        self,
        owner_id__eq: Optional[int],
        title__ilike: Optional[str],
        is_public__eq: Optional[bool],
        order_by: Optional[str],
        page: Optional[int],
        size: Optional[int],
        x_user_id: Optional[int],
        x_user_role: Optional[str],
    ) -> list[DeckDM]:
        """GET /decks/ — list decks; applies DeckScope row rule when X-User-Id is present."""

    @abstractmethod
    async def update_deck(self, deck_id: int, data: UpdateDeckDTO) -> DeckDM:
        """PATCH /decks/{deck_id} — partial update. 422 on empty body, 404 if absent."""

    @abstractmethod
    async def delete_deck(self, deck_id: int) -> None:
        """DELETE /decks/{deck_id} — remove a deck. 404 if absent."""
