# filters

---

## FilterField

```python
class UserFilter(FilterBase):
    name: FilterField[str]
```

Маркерная аннотация. Параметр типа определяет, какие операторы принимает поле,
— таблица в [DSL фильтров](../guide/filters.md).

---

## Op

```python
Op.eq  Op.neq  Op.gt  Op.lt  Op.gte  Op.lte
Op.ilike  Op.like  Op.in_  Op.is_null
```

Отображаются на методы-компараторы SQLAlchemy (`__eq__`, `ilike`, `in_`,
`is_`). Таблица «тип → операторы» — в `TYPES_AVAILABLE_OPS`.

---

## FilterBase

```python
FilterBase(**kwargs)          # field__op=value; одно field означает eq
```

Значения `None` пропускаются, неизвестные поля и операторы игнорируются.

| Член | |
|---|---|
| `as_fastapi_dep() -> Callable` | classmethod: зависимость, в сигнатуре которой по одному явному `Query` на пару «поле + оператор» |
| `active_expressions -> list[ParsedExpression]` | только то, что реально задано |
| `has_filter_for(field_name) -> bool` | |
| `order_by -> OrderBy \| None` | из аргумента `order_by` |

---

## OrderBy

```python
OrderBy("-age")     # по убыванию; "age" — по возрастанию
```

---

## apply_selection

```python
apply_selection(query, model, filter_obj: FilterBase)
```

Собирает `WHERE` из активных выражений фильтра, применяет сортировку и
подставляет join, если поле адресует связанную модель. Возвращает обычный
`Select` SQLAlchemy.
