"""
CardsController — uses manual init_http_routes() because one endpoint
has a non-standard path: POST /{card_id}/review.

AutoHttpController would generate POST / for any create_* method and
can't express /{card_id}/review without custom path specification.
Manual registration takes ten extra lines; the trade-off is explicit
control over every route path.

Contrast with UsersController / DecksController which are fully automatic.

Route map:
  POST   /cards/                    create_card
  GET    /cards/                    filter_cards
  POST   /cards/{card_id}/review    review_card   ← non-standard, needs manual reg
  GET    /cards/{card_id}           get_card
  PATCH  /cards/{card_id}           update_card
  DELETE /cards/{card_id}           delete_card
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination
from web_fractal.http.interfaces import HttpControllerABC
from web_fractal.mixins import NotExist

from .dtos import CardDM, CreateCardDTO, ReviewGradeDTO, UpdateCardDTO
from .filters import CardFilter
from .interfaces import CardServiceABC, CardsControllerABC


class CardsController(HttpControllerABC, CardsControllerABC):
    router = APIRouter(prefix="/cards", tags=["Cards"])

    svc: CardServiceABC  # archtool injects CardService instance
    # session_maker is set by bundle.py post-inject

    def init_http_routes(self) -> None:
        self.reg_route(self.create_card,  methods=["POST"],   path="/",                  response_model=CardDM)
        self.reg_route(self.filter_cards, methods=["GET"],    path="/",                  response_model=list[CardDM])
        self.reg_route(self.review_card,  methods=["POST"],   path="/{card_id}/review",  response_model=CardDM)
        self.reg_route(self.get_card,     methods=["GET"],    path="/{card_id}",         response_model=CardDM)
        self.reg_route(self.update_card,  methods=["PATCH"],  path="/{card_id}",         response_model=CardDM)
        self.reg_route(self.delete_card,  methods=["DELETE"], path="/{card_id}")

    async def create_card(self, data: CreateCardDTO) -> CardDM:
        async with UnitOfWork(self.session_maker) as uow:
            result = await self.svc.create([data.model_dump()], uow=uow)
            return result[0]

    async def get_card(self, card_id: int) -> CardDM:
        async with UnitOfWork(self.session_maker) as uow:
            try:
                return await self.svc.get(uow=uow, id=card_id)
            except NotExist:
                raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    async def filter_cards(
        self,
        deck_id__eq: Optional[int] = None,
        due_before: Optional[str] = None,
        order_by: Optional[str] = None,
        page: Optional[int] = None,
        size: Optional[int] = None,
    ) -> list[CardDM]:
        selection = CardFilter(deck_id__eq=deck_id__eq, order_by=order_by)
        if due_before:
            try:
                dt = datetime.fromisoformat(due_before)
                selection = CardFilter(deck_id__eq=deck_id__eq, due_date__lte=dt, order_by=order_by)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid due_before format: {due_before!r}")
        pag = Pagination(page=page or 1, size=size or 20)
        async with UnitOfWork(self.session_maker) as uow:
            return await self.svc.filter(selection, pag, uow=uow)

    async def update_card(self, card_id: int, data: UpdateCardDTO) -> CardDM:
        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise HTTPException(status_code=422, detail="Nothing to update")
        selection = CardFilter(id__eq=card_id)
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.update(selection, payload, uow=uow)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"Card {card_id} not found")
            return await self.svc.get(uow=uow, id=card_id)

    async def delete_card(self, card_id: int) -> None:
        async with UnitOfWork(self.session_maker) as uow:
            rows = await self.svc.delete(uow=uow, id=card_id)
            if rows == 0:
                raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    async def review_card(self, card_id: int, data: ReviewGradeDTO) -> CardDM:
        async with UnitOfWork(self.session_maker) as uow:
            try:
                return await self.svc.review(card_id, data.grade, uow=uow)
            except NotExist:
                raise HTTPException(status_code=404, detail=f"Card {card_id} not found")
