# Транспорты

HTTP — один протокол из нескольких. У всех общий `ProtocolControllerABC`,
поэтому доменный контроллер сохраняет форму независимо от того, что доставляет
вызов.

```python
from web_fractal.transports import (
    ProtocolControllerABC,
    KafkaControllerABC,
    GrpcServiceControllerABC,
    GraphQLControllerABC,
    initialize_all_protocols,
)
```

## Контракт

```python
class ProtocolControllerABC(ABC):
    @abstractmethod
    def init_handlers(self) -> None: ...

    async def on_startup(self) -> None: ...
    async def on_shutdown(self) -> None: ...
```

`init_handlers` — протокольный двойник `init_http_routes`: связать темы с
методами. `on_startup` и `on_shutdown` существуют потому, что консьюмеру,
gRPC-серверу или подписке нужен жизненный цикл, которого HTTP-роутеру не надо.

## Сборка

```python
await initialize_all_protocols(injector)
```

Находит в инжекторе все `ProtocolControllerABC`, вызывает `init_handlers()` и
ведёт хуки жизненного цикла — та же роль, что у `initialize_controllers_api` для
HTTP.

## Экстры

| Протокол | Экстра | Базовый класс |
|---|---|---|
| Kafka | `web_fractal[kafka]` | `KafkaControllerABC` |
| gRPC | `web_fractal[grpc]` | `GrpcServiceControllerABC` |
| GraphQL | `web_fractal[graphql]` | `GraphQLControllerABC` |

Клиентские библиотеки импортируются внутри адаптеров, поэтому объявление базовых
классов ничего не стоит, пока транспорт реально не запущен.
