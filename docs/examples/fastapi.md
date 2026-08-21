# FastAPI + archtool

A complete bounded context: model, filter, repository, controller, assembly.
This is the layout `wf add-module` generates and the one the sibling projects
use.

## Layout

```
app/orders/
├── interfaces.py     # ABCs — the contract of the context
├── dtos.py           # incoming Pydantic models
├── dms.py            # outgoing Pydantic models
├── models.py         # SQLAlchemy models
├── filters.py        # FilterBase subclasses
├── repos.py          # implementations
├── services.py       # business logic, when there is any
└── controllers.py    # HTTP routes
```

## Filter and repository

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
    session_maker: async_sessionmaker      # supplied by archtool
```

The annotation is the whole wiring: archtool sees `session_maker` and injects
the instance registered at assembly.

## Controller

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
                raise HTTPException(404, "Order not found")
```

Domain exceptions become HTTP codes here and nowhere deeper — the repository
raising `NotExist` knows nothing about HTTP, which is what lets the same
repository serve a Kafka consumer.

## Assembly

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

    import_all_models(Base=Base)       # complete metadata before wiring
    injector.inject()                  # layer violations surface here
    initialize_controllers_api(injector=injector, app=app)
    return injector
```

Order matters: async resources are registered before `inject()` because
archtool's discovery pass is synchronous and cannot create them, and
`import_all_models` runs first so `Base.metadata` is complete when Alembic or
`create_all` looks at it.

!!! warning "archtool 2.x"
    If `initialize_controllers_api` mounts nothing, check the archtool version —
    older releases exposed the registry as `_dependencies`, and reading the
    wrong name yields zero controllers **without an error**. Mounting with your
    own loop over `injector.dependencies` avoids the trap.

## Adding permissions

```python
class OrderScope(ScopeBase):
    row_rule = RowRule(lambda ctx, m: m.customer_id == ctx.user.id)

async def filter_orders(self, f, ctx = Depends(get_security_context)):
    async with UnitOfWork(self.session_maker) as uow:
        return await self.order_repo.filter(OrderScope.apply(f, ctx), pag, uow=uow)
```

One line, and the restriction is in the `WHERE` — not in a comprehension after
the rows have already been paginated.
