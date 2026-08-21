# Unit of Work

One session per operation, with an explicit commit.

```python
from web_fractal.db import UnitOfWork

async with UnitOfWork(session_maker) as uow:
    session = uow.get_session()
    session.add(obj)
    await session.commit()
```

Leaving the block commits on success and rolls back on an exception, then closes
the session. The explicit `commit()` is still the recommended style: it puts
commit failures inside your `try`, where you can answer them, instead of at the
edge of the block where you cannot.

## Registering objects

```python
await uow.register([obj], flush=True, refresh=True)
```

`register` adds objects to the session and remembers them, so `commit(refresh=True)`
can refresh them all afterwards — useful when the database fills in defaults you
intend to return.

## Base and helpers

`web_fractal.db` also carries the pieces that surround a session:

| | |
|---|---|
| `Base` | SQLAlchemy declarative base (`AsyncAttrs`), with `datetime → TIMESTAMP(timezone=True)` and mutable JSON in `type_annotation_map` |
| `paginate(query, Pagination)` | `LIMIT`/`OFFSET` from `page`/`size` |
| `apply_filters(query, Model, dict)` | the dict-based predecessor of the [filters DSL](filters.md) |
| `order_by_field(query, Model, "-age")` | ordering from a string |
| `copy_object(entity, uow, ...)` | deep copy of an ORM object, including secondary relations |
| `get_json_hash(data)` | stable hash of a JSON-serialisable value |

## With archtool

Repositories declare the factory as a class annotation and archtool supplies it:

```python
class UserRepo(GenericRepo):
    session_maker: async_sessionmaker
```

The session itself is passed as a method argument, never stored on `self` — the
controller owns the transaction boundary, the repository only runs queries.
