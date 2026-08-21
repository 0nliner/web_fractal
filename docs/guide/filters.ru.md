# DSL фильтров

`FilterBase` превращает класс с типизированными полями в query-параметры,
приведение типов и `WHERE`. Набор операторов выводится из типа поля, поэтому
`name__gte` у строки просто не существует.

```python
from web_fractal.filters import FilterBase, FilterField

class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    role: FilterField[Role]        # любой Enum
    created: FilterField[datetime]
```

## Операторы по типам

| Тип поля | Операторы |
|---|---|
| `str` | `eq` `neq` `ilike` `like` `in_` `is_null` |
| `int`, `float` | `eq` `neq` `gt` `lt` `gte` `lte` `in_` `is_null` |
| `date`, `datetime` | `eq` `neq` `gt` `lt` `gte` `lte` `is_null` |
| `bool` | `eq` `neq` `is_null` |
| `UUID` | `eq` `neq` `in_` `is_null` |
| `Enum` | `eq` `neq` `in_` `is_null` |

Таблица живёт в `TYPES_AVAILABLE_OPS`. Оператор, которого у типа нет,
**игнорируется**, а не отвергается: кривая строка запроса даёт более широкую
выборку, а не 500.

## Синтаксис запроса

Параметры — `field__op`; одно `field` означает `eq`:

```
?name__ilike=иван&age__gte=30&role__in_=admin,staff&created__lt=2026-01-01&order_by=-age
```

`order_by` принимает имя поля, префикс `-` — по убыванию.

## Как зависимость FastAPI

```python
UserFilterDep = UserFilter.as_fastapi_dep()

@router.get("/users")
async def list_users(f: Annotated[UserFilter, Depends(UserFilterDep)]):
    ...
```

`as_fastapi_dep()` собирает функцию, в сигнатуре которой по одному явному
`Query`-параметру на каждую пару «поле + оператор». Поэтому Swagger показывает
их, а не непрозрачный объект.

## Применение к запросу

```python
from web_fractal.filters import apply_selection

query = apply_selection(select(User), User, user_filter)
```

`apply_selection` заодно подставляет join, если поле фильтра адресует связанную
модель.

Старый словарный вариант никуда не делся:
`web_fractal.db.apply_filters(query, Model, {...})`.

## Что внутри фильтра

```python
f.active_expressions        # list[ParsedExpression] — только реально заданное
f.has_filter_for("name")    # bool
```

Пригодится в тестах и в правилах доступа, где нужно знать, ограничил ли
вызывающий поле до того, как вы ограничите его сами.
