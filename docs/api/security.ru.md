# security

`web_fractal.core.security`

---

## Контекст

```python
@dataclass
class UserPrincipal:
    id: Any = None
    roles: list[str] = []
    organization_id: Any | None = None
    extra: dict[str, Any] = {}

@dataclass
class EnvContext:
    ip: str | None = None
    tenant: str | None = None
    extra: dict[str, Any] = {}

@dataclass
class SecurityContext:
    user: UserPrincipal
    environment: EnvContext = EnvContext()
```

`SecurityContext.build(user, session=None)` — асинхронный classmethod для
случая, когда у вызывающего под рукой есть сессия.

---

## Правила

```python
AccessRule(allow_if=None, deny_if=None)
```
Ленивые предикаты по контексту. Оба `None` — разрешено. **`deny_if` побеждает**
`allow_if` — безопасное поведение, когда они расходятся.

```python
RowRule(condition: Callable[[SecurityContext, Model], Any])
```
Строит условие SQLAlchemy — вычисляется при сборке запроса, а не при объявлении
правила.

```python
FieldScope(visible: AccessRule | None = None, mask_with: Any = None)
FilterScope(rule: AccessRule | None = None, allowed_ops: list[Op] | None = None)
```
`allowed_ops=None` означает «разрешены все операторы».

---

## ScopeBase

```python
class EmployeeScope(ScopeBase, strict=False):
    bypass_if: Callable[[SecurityContext], bool] | None
    row_rule: RowRule | None
    field_scopes: dict[str, FieldScope]
    filter_scopes: dict[str, FilterScope]
```

У каждого наследника свои словари `field_scopes` / `filter_scopes` — они не
наследуются, поэтому дочерний скоуп не может незаметно расширить родительский.

| Classmethod | |
|---|---|
| `apply(filter_obj, ctx) -> FilterBase` | цепляет правило на строки, выбрасывает выражения с запрещёнными операторами |
| `evaluate_field(field_name, ctx) -> FieldDecision` | `.visible`, `.mask_with` |
| `evaluate_filter(field_name, op, ctx) -> bool` | можно ли вызывающему фильтровать это поле этим оператором |

---

## Исключения

`AccessDenied`, `FieldNotVisible`, `OperationNotAllowed`.
