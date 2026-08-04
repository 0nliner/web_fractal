"""
DecksController — also AutoHttpController, with ABAC scope integration.

The scope (DeckScope) is applied inside filter_decks when a user context
header is present.  In production you'd build the context from a JWT
middleware; here we use X-User-Id / X-User-Role headers so the behaviour
is testable without an auth stack.

Route map:
  POST   /decks/              create_deck
  GET    /decks/{deck_id}     get_deck
  GET    /decks/              filter_decks
  PATCH  /decks/{deck_id}     update_deck
  DELETE /decks/{deck_id}     delete_deck
"""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from web_fractal.core.security import SecurityContext, UserPrincipal
from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination
from web_fractal.http.auto_controller import AutoHttpController
from web_fractal.mixins import NotExist

from .dtos import CreateDeckDTO, DeckDM, UpdateDeckDTO
from .filters import DeckFilter
from .interfaces import DeckServiceABC, DecksControllerABC
from .scopes import DeckScope


class DecksController(AutoHttpController, DecksControllerABC):
    router = APIRouter(prefix="/decks", tags=["Decks"])

    svc: DeckServiceABC  # archtool injects DeckService instance
    # session_maker is set by bundle.py post-inject

    async def create_deck(self, data: CreateDeckDTO) -> DeckDM:
        async with UnitOfWork(self.session_maker) as uow:
            result = await self.svc.create([data.model_dump()], uow=uow)
            return result[0]

    async def get_deck(self, deck_id: int) -> DeckDM:
        async with UnitOfWork(self.session_maker) as uow:
            try:
                return await self.svc.get(uow=uow, id=deck_id)
            except NotExist:
                raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    async def filter_decks(
        self,
        owner_id__eq: Optional[int] = None,
        title__ilike: Optional[str] = None,
        is_public__eq: Optional[bool] = None,
        order_by: Optional[str] = None,
        page: Optional[int] = None,
        size: Optional[int] = None,
        x_user_id: Optional[int] = Header(None),
        x_user_role: Optional[str] = Header(None),
    ) -> list[DeckDM]:
        selection = DeckFilter(
            owner_id__eq=owner_id__eq,
            title__ilike=title__ilike,
            is_public__eq=is_public__eq,
            order_by=order_by,
        )
        if x_user_id is not None:
            ctx = SecurityContext(
                user=UserPrincipal(id=x_user_id, extra={"role": x_user_role or "student"})
            )
            selection = DeckScope.apply(selection, ctx)

        pag = Pagination(page=page or 1, size=size or 20)
        async with UnitOfWork(self.session_maker) as uow:
            return await self.svc.filter(selection, pag, uow=uow)

    async def update_deck(self, deck_id: int, data: UpdateDeckDTO) -> DeckDM:
        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise HTTPException(status_code=422, detail="Nothing to update")
        selection = DeckFilter(id__eq=deck_id)
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.update(selection, payload, uow=uow)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
            return await self.svc.get(uow=uow, id=deck_id)

    async def delete_deck(self, deck_id: int) -> None:
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.delete(uow=uow, id=deck_id)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
