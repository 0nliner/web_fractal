# db

`web_fractal.db` — session lifecycle and the helpers that surround a query.

---

## UnitOfWork

```python
UnitOfWork(session_maker: async_sessionmaker)
```

Async context manager. On exit: commits on success, rolls back on exception,
then closes the session.

| Method | |
|---|---|
| `get_session() -> AsyncSession` | the live session; raises if used outside the context |
| `await commit(refresh: bool = False)` | commit; with `refresh=True` refreshes everything passed to `register` |
| `await rollback()` | |
| `await close()` | |
| `await register(objects: list, refresh: bool = False, flush: bool = False)` | `session.add_all` + remember for later refresh |

The attribute `session` is also available directly.

---

## Base

SQLAlchemy declarative base (`AsyncAttrs` + `DeclarativeBase`) with a
`type_annotation_map` that maps `datetime` to `TIMESTAMP(timezone=True)` and
`dict[str, Any]` to mutable JSON.

---

## Query helpers

```python
paginate(query, pag_info: Pagination)
```
`LIMIT size OFFSET (page - 1) * size`.

```python
apply_filters(q, apply_to, filters: dict, ignore: list[str] | None = None)
```
Equality predicates from a dict. The typed alternative is
[`apply_selection`](filters.md).

```python
order_by_field(q, model, field: str)
```
`"age"` ascending, `"-age"` descending.

```python
await copy_object(entity, uow, use_same=None, ignore=None, flush=True, all_objects=None, **overrides)
```
Deep copy of an ORM object: primary keys are skipped, many-to-one parents are
not copied, and secondary relations are copied recursively. `overrides` set
fields on the copy.

```python
get_json_hash(data, hash_algorithm: str = "sha256") -> str
```
Stable hash of a JSON-serialisable value — keys are sorted, so equal content
gives an equal hash.

```python
get_no_db_engine(dsn) -> Engine      # engine without the database in the DSN
get_db_name(dsn) -> str
```

---

## Base classes

**`BaseRepo[T, R]`** — `session_maker` annotation plus `_to_dto` / `_to_dto_list`
and the `in_session` / `get_session` context managers, for repositories that are
not built on [`GenericRepo`](mixins.md).

**`Dated`** — `created_at` / `updated_at` mixin.

**`BaseTypedDict`** — dict subclass with `.not_blank`, which drops `UNSET`
values.
