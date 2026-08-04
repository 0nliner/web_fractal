"""
Phase 6: Multi-protocol controller ABCs.

ProtocolControllerABC is the root ABC for all protocol adapters.
initialize_all_protocols() discovers them via archtool injector and calls init_handlers().
"""
from abc import ABC, abstractmethod
from typing import Any, Optional


class ProtocolControllerABC(ABC):
    """Root ABC for all protocol controllers (HTTP, Kafka, gRPC, GraphQL)."""

    @abstractmethod
    def init_handlers(self) -> None: ...

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass


class KafkaControllerABC(ProtocolControllerABC, ABC):
    """
    ABC for Kafka consumer controllers.
    Requires: aiokafka

    class OrdersKafkaController(KafkaControllerABC):
        def init_handlers(self):
            self.reg_handler("orders.created", self.handle_order_created, group_id="my-service")
    """

    _handlers: dict

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._handlers = {}

    def reg_handler(self, topic: str, handler, group_id: Optional[str] = None) -> None:
        self._handlers[topic] = {"handler": handler, "group_id": group_id}

    def subscribe(self) -> None:
        raise NotImplementedError(
            "subscribe() requires aiokafka. Install web_fractal[kafka] and implement subscribe()."
        )


class GrpcServiceControllerABC(ProtocolControllerABC, ABC):
    """
    ABC for gRPC service controllers.
    Requires: grpclib

    class UsersGrpcController(GrpcServiceControllerABC):
        service_name = "UsersService"
        def init_handlers(self):
            self.reg_handler("GetUser", self.get_user)
    """

    service_name: str
    _handlers: dict

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._handlers = {}

    def reg_handler(
        self,
        rpc_name: str,
        handler,
        stream_request: bool = False,
        stream_response: bool = False,
    ) -> None:
        self._handlers[rpc_name] = {
            "handler": handler,
            "stream_request": stream_request,
            "stream_response": stream_response,
        }


class GraphQLControllerABC(ProtocolControllerABC, ABC):
    """
    ABC for GraphQL resolver controllers.
    Requires: strawberry-graphql

    class UsersGraphQLController(GraphQLControllerABC):
        def init_handlers(self):
            self.reg_query("users", self.resolve_users)
    """

    _queries: dict
    _mutations: dict
    _subscriptions: dict

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._queries = {}
        cls._mutations = {}
        cls._subscriptions = {}

    def reg_query(self, name: str, handler) -> None:
        self._queries[name] = handler

    def reg_mutation(self, name: str, handler) -> None:
        self._mutations[name] = handler

    def reg_subscription(self, name: str, handler) -> None:
        self._subscriptions[name] = handler


def initialize_all_protocols(
    injector: Any,
    *,
    app: Any = None,
    grpc_server: Any = None,
) -> None:
    """
    Iterate over archtool injector dependencies, call init_handlers() on each
    ProtocolControllerABC instance, then perform protocol-specific registration.

    Args:
        injector:    archtool DependencyInjector
        app:         FastAPI app instance (for HTTP controllers)
        grpc_server: grpclib.Server instance (for gRPC controllers)
    """
    from web_fractal.http.interfaces import HttpControllerABC

    deps = (
        injector.dependencies
        if hasattr(injector, "dependencies")
        else getattr(injector, "_dependencies", {})
    )

    for instance in deps.values():
        if not isinstance(instance, ProtocolControllerABC):
            continue

        instance.init_handlers()

        if isinstance(instance, HttpControllerABC) and app is not None:
            app.include_router(instance.router)
        elif isinstance(instance, GrpcServiceControllerABC) and grpc_server is not None:
            pass  # grpc_server.add_service(instance.servicer) — requires grpclib
        elif isinstance(instance, KafkaControllerABC):
            pass  # consumer starts via instance.subscribe() in on_startup
