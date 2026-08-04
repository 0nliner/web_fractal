from abc import ABC, abstractmethod
from typing import Unpack

from fastapi import APIRouter
from .types_ import RegRoutesParams


class HttpControllerABC(ABC):
    router: APIRouter

    def __init__(self) -> None:
        # Give each instance its own fresh router so routes don't accumulate
        # across multiple instances of the same controller class (e.g. in tests).
        cls_router = type(self).__dict__.get("router")
        if cls_router is not None:
            self.router = APIRouter(
                prefix=cls_router.prefix,
                tags=list(cls_router.tags or []),
            )

    @abstractmethod
    def init_http_routes(self):
        ...

    def reg_route(self, method, **overwrites: Unpack[RegRoutesParams]):
        payload = {"path": f"/{method.__name__}", "endpoint": method, "operation_id": method.__name__, **overwrites}
        self.router.add_api_route(**payload)
