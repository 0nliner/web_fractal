# Filters DSL

`FilterBase` turns a class of typed fields into query parameters, coercion and a
`WHERE` clause. The operators available for a field are derived from its type,
so `name__gte` cannot exist for a `str`.

```python
from web_fractal.filters import FilterBase, FilterField

class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    role: FilterField[Role]        # any Enum
    created: FilterField[datetime]
```

## Operators by type

| Field type | Operators |
|---|---|
| `str` | `eq` `neq` `ilike` `like` `in_` `is_null` |
| `int`, `float` | `eq` `neq` `gt` `lt` `gte` `lte` `in_` `is_null` |
| `date`, `datetime` | `eq` `neq` `gt` `lt` `gte` `lte` `is_null` |
| `bool` | `eq` `neq` `is_null` |
| `UUID` | `eq` `neq` `in_` `is_null` |
| `Enum` | `eq` `neq` `in_` `is_null` |

The mapping lives in `TYPES_AVAILABLE_OPS`. An operator that a type does not
support is **ignored**, not rejected — a malformed query string degrades to a
broader result set instead of a 500.

## Query syntax

Parameters are `field__op`; `field` alone means `eq`:

```
?name__ilike=иван&age__gte=30&role__in_=admin,staff&created__lt=2026-01-01&order_by=-age
```

`order_by` takes a field name, `-` prefix for descending.

## As a FastAPI dependency

```python
UserFilterDep = UserFilter.as_fastapi_dep()

@router.get("/users")
async def list_users(f: Annotated[UserFilter, Depends(UserFilterDep)]):
    ...
```

`as_fastapi_dep()` builds a callable whose signature holds one explicit `Query`
parameter per field/operator pair — which is why Swagger shows them instead of
an opaque object.

## Applying to a query

```python
from web_fractal.filters import apply_selection

query = apply_selection(select(User), User, user_filter)
```

`apply_selection` also joins related models when a filter field addresses one.

For the older dict-based style, `web_fractal.db.apply_filters(query, Model, {...})`
is still there.

## Inspecting a filter

```python
f.active_expressions        # list[ParsedExpression] — only what was actually set
f.has_filter_for("name")    # bool
```

Both are useful in tests and in scope rules, where you need to know whether the
caller constrained a field before you constrain it further.
