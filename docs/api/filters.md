# filters

---

## FilterField

```python
class UserFilter(FilterBase):
    name: FilterField[str]
```

A marker annotation. The type parameter decides which operators the field
accepts — see the table in [Filters DSL](../guide/filters.md).

---

## Op

```python
Op.eq  Op.neq  Op.gt  Op.lt  Op.gte  Op.lte
Op.ilike  Op.like  Op.in_  Op.is_null
```

Mapped onto SQLAlchemy comparator methods (`__eq__`, `ilike`, `in_`, `is_`).
`TYPES_AVAILABLE_OPS` holds the type → operators table.

---

## FilterBase

```python
FilterBase(**kwargs)          # field__op=value; bare field means eq
```

`None` values are skipped, unknown fields and unknown operators are ignored.

| Member | |
|---|---|
| `as_fastapi_dep() -> Callable` | classmethod: a dependency whose signature holds one explicit `Query` per field/operator pair |
| `active_expressions -> list[ParsedExpression]` | only what was actually set |
| `has_filter_for(field_name) -> bool` | |
| `order_by -> OrderBy \| None` | from the `order_by` argument |

---

## OrderBy

```python
OrderBy("-age")     # descending; "age" ascending
```

---

## apply_selection

```python
apply_selection(query, model, filter_obj: FilterBase)
```

Builds the `WHERE` from the filter's active expressions, applies ordering, and
joins related models when a field addresses one. Returns an ordinary
SQLAlchemy `Select`.
