# Единица работы

Одна сессия на операцию и явный commit.

```python
from web_fractal.db import UnitOfWork

async with UnitOfWork(session_maker) as uow:
    session = uow.get_session()
    session.add(obj)
    await session.commit()
```

Выход из блока коммитит при успехе и откатывает при исключении, затем закрывает
сессию. Явный `commit()` всё равно остаётся рекомендуемым стилем: он помещает
ошибку коммита внутрь вашего `try`, где на неё можно ответить, а не на границе
блока, где уже нельзя.

## Регистрация объектов

```python
await uow.register([obj], flush=True, refresh=True)
```

`register` добавляет объекты в сессию и запоминает их, поэтому
`commit(refresh=True)` потом обновит их все — удобно, когда база проставляет
значения по умолчанию, которые вы собираетесь вернуть.

## База и хелперы

В `web_fractal.db` лежит и то, что окружает сессию:

| | |
|---|---|
| `Base` | declarative-база SQLAlchemy (`AsyncAttrs`) с `datetime → TIMESTAMP(timezone=True)` и мутабельным JSON в `type_annotation_map` |
| `paginate(query, Pagination)` | `LIMIT`/`OFFSET` из `page`/`size` |
| `apply_filters(query, Model, dict)` | словарный предшественник [DSL фильтров](filters.md) |
| `order_by_field(query, Model, "-age")` | сортировка из строки |
| `copy_object(entity, uow, ...)` | глубокая копия ORM-объекта вместе со связями через secondary |
| `get_json_hash(data)` | устойчивый хеш JSON-совместимого значения |

## Вместе с archtool

Репозиторий объявляет фабрику классовой аннотацией, archtool её подставляет:

```python
class UserRepo(GenericRepo):
    session_maker: async_sessionmaker
```

Саму сессию передают аргументом метода и никогда не держат в `self`: границей
транзакции владеет контроллер, репозиторий только выполняет запросы.
