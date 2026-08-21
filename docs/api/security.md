# security

`web_fractal.core.security`

---

## Context

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

`SecurityContext.build(user, session=None)` is an async classmethod for building
the context where the caller has a session at hand.

---

## Rules

```python
AccessRule(allow_if=None, deny_if=None)
```
Lazy predicates over the context. Both `None` means allow. **`deny_if` wins**
over `allow_if`, which is the safe default when the two disagree.

```python
RowRule(condition: Callable[[SecurityContext, Model], Any])
```
Builds a SQLAlchemy condition — evaluated when the query is assembled, not when
the rule is declared.

```python
FieldScope(visible: AccessRule | None = None, mask_with: Any = None)
FilterScope(rule: AccessRule | None = None, allowed_ops: list[Op] | None = None)
```
`allowed_ops=None` means every operator is permitted.

---

## ScopeBase

```python
class EmployeeScope(ScopeBase, strict=False):
    bypass_if: Callable[[SecurityContext], bool] | None
    row_rule: RowRule | None
    field_scopes: dict[str, FieldScope]
    filter_scopes: dict[str, FilterScope]
```

Each subclass gets its own `field_scopes` / `filter_scopes` dicts — they are not
inherited, so a child scope cannot silently widen its parent.

| Classmethod | |
|---|---|
| `apply(filter_obj, ctx) -> FilterBase` | attaches the row rule, drops expressions using disallowed operators |
| `evaluate_field(field_name, ctx) -> FieldDecision` | `.visible`, `.mask_with` |
| `evaluate_filter(field_name, op, ctx) -> bool` | may the caller filter this field with this operator |

---

## Exceptions

`AccessDenied`, `FieldNotVisible`, `OperationNotAllowed`.
