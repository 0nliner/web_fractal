"""
UsersController — demonstrates AutoHttpController.

Key pattern: services are INSTANCE ATTRIBUTES set once at startup by
archtool's DependencyInjector.  No FastAPI Depends() anywhere — not in
method signatures, not in module-level factories.  Each request creates
its own UnitOfWork and commits (or rolls back) independently.

Route map (auto-inferred from method names):
  POST   /users/              create_user
  GET    /users/{user_id}     get_user
  GET    /users/              filter_users
  PATCH  /users/{user_id}     update_user
  DELETE /users/{user_id}     delete_user
"""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from web_fractal.core.security import SecurityContext, UserPrincipal
from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination
from web_fractal.http.auto_controller import AutoHttpController
from web_fractal.mixins import NotExist

from .dtos import CreateUserDTO, UpdateUserDTO, UserDM
from .filters import UserFilter
from .interfaces import UserServiceABC, UsersControllerABC
from .scopes import UserScope


class UsersController(AutoHttpController, UsersControllerABC):
    router = APIRouter(prefix="/users", tags=["Users"])

    # ── archtool injects these once at startup ──────────────────────────────
    svc: UserServiceABC
    # session_maker is set by bundle.py post-inject (not annotated — outside project root)
    # ────────────────────────────────────────────────────────────────────────

    async def create_user(self, data: CreateUserDTO) -> UserDM:
        async with UnitOfWork(self.session_maker) as uow:
            result = await self.svc.create([data.model_dump()], uow=uow)
            return result[0]

    async def get_user(self, user_id: int) -> UserDM:
        async with UnitOfWork(self.session_maker) as uow:
            try:
                return await self.svc.get(uow=uow, id=user_id)
            except NotExist:
                raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    async def filter_users(
        self,
        username__ilike: Optional[str] = None,
        email__ilike: Optional[str] = None,
        role__eq: Optional[str] = None,
        is_active__eq: Optional[bool] = None,
        order_by: Optional[str] = None,
        page: Optional[int] = None,
        size: Optional[int] = None,
        x_user_id: Optional[int] = Header(None),
        x_user_role: Optional[str] = Header(None),
    ) -> list[UserDM]:
        selection = UserFilter(
            username__ilike=username__ilike,
            email__ilike=email__ilike,
            role__eq=role__eq,
            is_active__eq=is_active__eq,
            order_by=order_by,
        )
        pag = Pagination(page=page or 1, size=size or 20)
        async with UnitOfWork(self.session_maker) as uow:
            users = await self.svc.filter(selection, pag, uow=uow)

        if x_user_id is None:
            return users

        ctx = SecurityContext(
            user=UserPrincipal(id=x_user_id, extra={"role": x_user_role or "student"})
        )
        decision = UserScope.evaluate_field("email", ctx)
        if decision.visible:
            return users
        return [u.model_copy(update={"email": decision.mask_with}) for u in users]

    async def update_user(self, user_id: int, data: UpdateUserDTO) -> UserDM:
        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise HTTPException(status_code=422, detail="Nothing to update")
        selection = UserFilter(id__eq=user_id)
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.update(selection, payload, uow=uow)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"User {user_id} not found")
            return await self.svc.get(uow=uow, id=user_id)

    async def delete_user(self, user_id: int) -> None:
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.delete(uow=uow, id=user_id)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"User {user_id} not found")
