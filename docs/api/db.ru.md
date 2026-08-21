# db

`web_fractal.db` — жизненный цикл сессии и всё, что окружает запрос.

---

## UnitOfWork

```python
UnitOfWork(session_maker: async_sessionmaker)
```

Асинхронный контекстный менеджер. На выходе: коммит при успехе, откат при
исключении, затем закрытие сессии.

| Метод | |
|---|---|
| `get_session() -> AsyncSession` | живая сессия; вне контекста бросает исключение |
| `await commit(refresh: bool = False)` | коммит; с `refresh=True` обновляет всё, что передавали в `register` |
| `await rollback()` | |
| `await close()` | |
| `await register(objects: list, refresh: bool = False, flush: bool = False)` | `session.add_all` + запомнить для последующего refresh |

Атрибут `session` доступен и напрямую.

---

## Base

Declarative-база SQLAlchemy (`AsyncAttrs` + `DeclarativeBase`) с
`type_annotation_map`, где `datetime` отображается на `TIMESTAMP(timezone=True)`,
а `dict[str, Any]` — на мутабельный JSON.

---

## Помощники запроса

```python
paginate(query, pag_info: Pagination)
```
`LIMIT size OFFSET (page - 1) * size`.

```python
apply_filters(q, apply_to, filters: dict, ignore: list[str] | None = None)
```
Предикаты равенства из словаря. Типизированная альтернатива —
[`apply_selection`](filters.md).

```python
order_by_field(q, model, field: str)
```
`"age"` — по возрастанию, `"-age"` — по убыванию.

```python
await copy_object(entity, uow, use_same=None, ignore=None, flush=True, all_objects=None, **overrides)
```
Глубокая копия ORM-объекта: первичные ключи пропускаются, родители
many-to-one не копируются, связи через secondary копируются рекурсивно.
`overrides` проставляет поля копии.

```python
get_json_hash(data, hash_algorithm: str = "sha256") -> str
```
Устойчивый хеш JSON-совместимого значения: ключи сортируются, поэтому равное
содержимое даёт равный хеш.

```python
get_no_db_engine(dsn) -> Engine      # движок без имени базы в DSN
get_db_name(dsn) -> str
```

---

## Базовые классы

**`BaseRepo[T, R]`** — аннотация `session_maker`, методы `_to_dto` /
`_to_dto_list` и контекстные менеджеры `in_session` / `get_session` для
репозиториев, не построенных на [`GenericRepo`](mixins.md).

**`Dated`** — миксин `created_at` / `updated_at`.

**`BaseTypedDict`** — наследник dict со свойством `.not_blank`, выбрасывающим
значения `UNSET`.
