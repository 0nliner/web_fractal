# FastAPI + archtool

Ограниченный контекст целиком: модель, фильтр, репозиторий, контроллер, сборка.
Такую раскладку генерирует `wf add-module`, и её же используют соседние проекты.

## Раскладка

```
app/orders/
├── interfaces.py     # ABC — контракт контекста
├── dtos.py           # входящие Pydantic-модели
├── dms.py            # исходящие Pydantic-модели
├── models.py         # модели SQLAlchemy
├── filters.py        # наследники FilterBase
├── repos.py          # реализации
├── services.py       # бизнес-логика, если она есть
└── controllers.py    # HTTP-маршруты
```

## Фильтр и репозиторий

```python
# app/orders/filters.py
from web_fractal.filters import FilterBase, FilterField

class OrderFilter(FilterBase):
    status: FilterField[OrderStatus]
    total: FilterField[int]
    created: FilterField[datetime]
```

```python
# app/orders/repos.py
from sqlalchemy.ext.asyncio import async_sessionmaker
from web_fractal.mixins import GenericRepo

from .models import Order
from .dms import OrderDM

class OrderRepo(GenericRepo):
    model = Order
    dm_class = OrderDM
    session_maker: async_sessionmaker      # подставит archtool
```

Аннотация — и есть вся разводка: archtool видит `session_maker` и подставляет
экземпляр, зарегистрированный при сборке.

## Контроллер

```python
# app/orders/controllers.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination
from web_fractal.http.interfaces import HttpControllerABC
from web_fractal.mixins import NotExist

from .filters import OrderFilter
from .interfaces import OrderRepoABC

OrderFilterDep = OrderFilter.as_fastapi_dep()

class OrderController(HttpControllerABC):
    router = APIRouter(prefix="/orders", tags=["orders"])
    session_maker: async_sessionmaker
    order_repo: OrderRepoABC

    def init_http_routes(self) -> None:
        self.reg_route(self.filter_orders, methods=["GET"], path="")
        self.reg_route(self.get_order, methods=["GET"], path="/{pk}")

    async def filter_orders(
        self,
        f: Annotated[OrderFilter, Depends(OrderFilterDep)],
        pag: Pagination = Depends(),
    ) -> list[OrderDM]:
        async with UnitOfWork(self.session_maker) as uow:
            return await self.order_repo.filter(f, pag, uow=uow)

    async def get_order(self, pk: int) -> OrderDM:
        async with UnitOfWork(self.session_maker) as uow:
            try:
                return await self.order_repo.get(uow=uow, id=pk)
            except NotExist:
                raise HTTPException(404, "Заказ не найден")
```

Доменные исключения превращаются в HTTP-коды здесь и нигде глубже: репозиторий,
бросающий `NotExist`, ничего не знает про HTTP, — благодаря этому тот же
репозиторий обслуживает и консьюмер Kafka.

## Сборка

```python
# app/archtool_conf/bundle.py
from archtool.dependency_injector import DependencyInjector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from web_fractal.building_utils import import_all_models, initialize_controllers_api
from web_fractal.db import Base

def bundle(app: FastAPI) -> DependencyInjector:
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    injector = DependencyInjector(modules_list=APPS, layers=LAYERS, project_root=ROOT)
    injector.register(key=async_sessionmaker, value=session_maker, inject_into=False)

    import_all_models(Base=Base)       # полная metadata до разводки
    injector.inject()                  # нарушения слоёв всплывают здесь
    initialize_controllers_api(injector=injector, app=app)
    return injector
```

Порядок важен: async-ресурсы регистрируются до `inject()`, потому что проход
обнаружения у archtool синхронный и создать их не может, а `import_all_models`
идёт первым, чтобы `Base.metadata` была полной, когда в неё заглянут alembic
или `create_all`.

!!! warning "archtool 2.x"
    Если `initialize_controllers_api` ничего не смонтировала — проверьте версию
    archtool: в старых выпусках реестр назывался `_dependencies`, и чтение
    неверного имени даёт ноль контроллеров **без единой ошибки**. Монтирование
    своим циклом по `injector.dependencies` обходит ловушку.

## Добавляем права

```python
class OrderScope(ScopeBase):
    row_rule = RowRule(lambda ctx, m: m.customer_id == ctx.user.id)

async def filter_orders(self, f, ctx = Depends(get_security_context)):
    async with UnitOfWork(self.session_maker) as uow:
        return await self.order_repo.filter(OrderScope.apply(f, ctx), pag, uow=uow)
```

Одна строка — и ограничение оказывается в `WHERE`, а не в списковом включении
после того, как строки уже отпагинированы.
