# Transports

HTTP is one protocol among several. All of them share `ProtocolControllerABC`,
so a domain controller keeps the same shape regardless of what carries the call.

```python
from web_fractal.transports import (
    ProtocolControllerABC,
    KafkaControllerABC,
    GrpcServiceControllerABC,
    GraphQLControllerABC,
    initialize_all_protocols,
)
```

## The contract

```python
class ProtocolControllerABC(ABC):
    @abstractmethod
    def init_handlers(self) -> None: ...

    async def on_startup(self) -> None: ...
    async def on_shutdown(self) -> None: ...
```

`init_handlers` is the protocol-specific twin of `init_http_routes`: bind
subjects to methods. `on_startup` / `on_shutdown` exist because a consumer, a
gRPC server or a subscription needs a lifecycle that an HTTP router does not.

## Assembly

```python
await initialize_all_protocols(injector)
```

It discovers every `ProtocolControllerABC` in the injector, calls
`init_handlers()` and drives the lifecycle hooks — the same role
`initialize_controllers_api` plays for HTTP.

## Extras

| Protocol | Extra | Base class |
|---|---|---|
| Kafka | `web_fractal[kafka]` | `KafkaControllerABC` |
| gRPC | `web_fractal[grpc]` | `GrpcServiceControllerABC` |
| GraphQL | `web_fractal[graphql]` | `GraphQLControllerABC` |

The client libraries are imported inside the adapters, so declaring the base
classes costs nothing until you actually run that transport.
