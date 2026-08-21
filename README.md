# web_fractal

Конструктор веб-приложений поверх SQLAlchemy и Pydantic: типобезопасный DSL
фильтров, CRUD-миксины, ABAC-правила доступа, контроллеры для нескольких
транспортов. Ядро не привязано к веб-фреймворку — интеграции подключаются
экстрами.

```bash
pip install web_fractal              # ядро: db, dtos, filters, mixins, security
pip install "web_fractal[fastapi]"   # + контроллеры и сборка FastAPI-приложения
```

## Что внутри

| Модуль | Зачем |
|---|---|
| `web_fractal.db` | `Base`, `UnitOfWork`, `paginate`, `apply_filters`, `copy_object` |
| `web_fractal.dtos` | Pydantic-база с `.not_blank`, `Pagination`, `MessageDTO` |
| `web_fractal.types` | `Unset`/`UNSET` — sentinel «не фильтровать», в отличие от `None` |
| `web_fractal.filters` | `FilterBase` + `FilterField[T]`: DSL фильтрации с автогенерацией query-параметров |
| `web_fractal.mixins` | `GenericRepo`, `GenericService` — CRUD без копипасты |
| `web_fractal.core.security` | ABAC: `SecurityContext`, `AccessRule`, `RowRule`, `FieldScope` |
| `web_fractal.http` | `HttpControllerABC`, `AutoHttpController` (требует экстру `fastapi`) |
| `web_fractal.building_utils` | Сборка FastAPI-приложения из archtool-инжектора (экстра `fastapi`) |
| `web_fractal.transports` | Контроллеры Kafka / gRPC / GraphQL (свои экстры) |

## Фильтры

```python
from web_fractal.filters import FilterBase, FilterField

class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]

# FastAPI-зависимость с явными query-параметрами в Swagger
UserFilterDep = UserFilter.as_fastapi_dep()
```

## Единица работы

```python
from web_fractal.db import UnitOfWork

async with UnitOfWork(session_maker) as uow:
    session = uow.get_session()
    ...
    await session.commit()
```

## Экстры

| Экстра | Что включает |
|---|---|
| `fastapi` | HTTP-контроллеры, middlewares, сборка приложения |
| `aiohttp` | `utils.download_large_file` |
| `kafka`, `grpc`, `graphql` | соответствующие транспорты |
| `django` | адаптеры для Django-проектов |

Пакет не импортирует подмодули на загрузке (PEP 562): `import web_fractal.db`
не требует ни FastAPI, ни aiohttp. Публичные имена доступны и из корня —
`from web_fractal import UnitOfWork` — но резолвятся лениво, при первом
обращении.

## Разработка

```bash
uv sync --extra dev
pytest
```

MIT.
