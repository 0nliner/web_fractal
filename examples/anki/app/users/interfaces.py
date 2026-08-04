from abc import abstractmethod
from typing import Any, Optional

from archtool.layers.default_layer_interfaces import ABCController, ABCRepo, ABCService

from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination

from .dtos import CreateUserDTO, UpdateUserDTO, UserDM
from .filters import UserFilter


class UserRepoABC(ABCRepo):
    """CRUD repository contract for the User model."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[UserDM]:
        """Bulk-insert users and return their domain models."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> UserDM:
        """Return a single user matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[UserDM]:
        """Return a single user or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: UserFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[UserDM]:
        """Return a filtered, paginated list of users."""

    @abstractmethod
    async def update(self, selection: UserFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all users matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete users matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: UserFilter, *, uow: UnitOfWork) -> int:
        """Return the number of users matching selection."""


class UserServiceABC(ABCService):
    """Business-logic contract for the User domain."""

    @abstractmethod
    async def create(self, data: list[dict], *, uow: UnitOfWork) -> list[UserDM]:
        """Create users, invoking before_create / after_create hooks."""

    @abstractmethod
    async def get(self, *, uow: UnitOfWork, **filters: Any) -> UserDM:
        """Return a single user matching scalar filters. Raises NotExist if absent."""

    @abstractmethod
    async def get_or_none(self, *, uow: UnitOfWork, **filters: Any) -> Optional[UserDM]:
        """Return a single user or None if not found."""

    @abstractmethod
    async def filter(
        self,
        selection: UserFilter,
        pag: Pagination,
        *,
        uow: UnitOfWork,
        eager_load: list[str] = [],
    ) -> list[UserDM]:
        """Return a filtered, paginated list of users."""

    @abstractmethod
    async def update(self, selection: UserFilter, payload: dict, *, uow: UnitOfWork) -> int:
        """Apply payload to all users matching selection. Returns row count."""

    @abstractmethod
    async def delete(self, *, uow: UnitOfWork, **filters: Any) -> int:
        """Delete users matching scalar filters. Returns row count."""

    @abstractmethod
    async def count(self, selection: UserFilter, *, uow: UnitOfWork) -> int:
        """Return the number of users matching selection."""


class UsersControllerABC(ABCController):
    """HTTP controller contract for the /users resource."""

    @abstractmethod
    def init_http_routes(self) -> None:
        """Register all HTTP routes on self.router."""

    @abstractmethod
    async def create_user(self, data: CreateUserDTO) -> UserDM:
        """POST /users/ — create a new user."""

    @abstractmethod
    async def get_user(self, user_id: int) -> UserDM:
        """GET /users/{user_id} — retrieve a user by id. 404 if absent."""

    @abstractmethod
    async def filter_users(
        self,
        username__ilike: Optional[str],
        email__ilike: Optional[str],
        role__eq: Optional[str],
        is_active__eq: Optional[bool],
        order_by: Optional[str],
        page: Optional[int],
        size: Optional[int],
        x_user_id: Optional[int],
        x_user_role: Optional[str],
    ) -> list[UserDM]:
        """GET /users/ — list users with DSL filters; masks email via UserScope when X-User-Id is present."""

    @abstractmethod
    async def update_user(self, user_id: int, data: UpdateUserDTO) -> UserDM:
        """PATCH /users/{user_id} — partial update. 422 on empty body, 404 if absent."""

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        """DELETE /users/{user_id} — remove a user. 404 if absent."""
