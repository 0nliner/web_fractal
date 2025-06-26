from abc import ABC, abstractmethod
from typing import Unpack

from fastapi import APIRouter
from .types_ import RegRoutesParams


class HttpControllerABC(ABC):
    router: APIRouter

    @abstractmethod
    def init_http_routes(self):
        ...

    def reg_route(self, method, **overwrites: Unpack[RegRoutesParams]):
        payload = {"path": f"/{method.__name__}", "endpoint": method, "operation_id": method.__name__, **overwrites}
        self.router.add_api_route(**payload)

