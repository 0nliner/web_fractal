# Security (ABAC)

Attribute-based access control that folds into the filter **before** it becomes
SQL. Nothing is filtered in Python after the rows arrive — that is the pattern
that leaks data the moment someone adds pagination.

## Context

```python
from web_fractal.core.security import SecurityContext, UserPrincipal, EnvContext

ctx = SecurityContext(
    user=UserPrincipal(id=42, roles=["hr"], organization_id=7),
    environment=EnvContext(ip="10.0.0.1", tenant="acme"),
)
```

## Scope

```python
from web_fractal.core.security import ScopeBase, RowRule, FieldScope, FilterScope, AccessRule
from web_fractal.filters import Op

class EmployeeScope(ScopeBase, strict=False):
    bypass_if = lambda ctx: "admin" in ctx.user.roles

    row_rule = RowRule(lambda ctx, m: m.org_id == ctx.user.organization_id)

    field_scopes = {
        "salary": FieldScope(visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles)),
    }
    filter_scopes = {
        "salary": FilterScope(allowed_ops=[Op.eq]),
    }
```

| Declaration | Effect |
|---|---|
| `bypass_if` | short-circuits the whole scope — the classic admin escape hatch |
| `row_rule` | a condition appended to the query: which rows exist at all |
| `field_scopes` | whether a field is visible, and what to mask it with |
| `filter_scopes` | which operators a caller may use on a field |

`strict=True` denies anything not explicitly allowed; the default is permissive.

## Applying

```python
secured = EmployeeScope.apply(employee_filter, ctx)   # -> FilterBase
rows = await repo.filter(secured, pag, uow=uow)
```

`apply` returns the same filter object carrying the row rule, with disallowed
operator expressions dropped.

## Field decisions

```python
decision = EmployeeScope.evaluate_field("salary", ctx)
decision.visible      # bool
decision.mask_with    # value to substitute when hidden
```

Use it when serialising: a hidden field becomes `mask_with` rather than
disappearing, so the response shape stays stable for clients.

```python
EmployeeScope.evaluate_filter("salary", Op.gt, ctx)   # False → probing is blocked
```

`filter_scopes` exists for exactly that: a field may be *visible* to nobody yet
still leak through `salary__gt=100000` binary search if operators are not
constrained.

## Exceptions

`AccessDenied`, `FieldNotVisible`, `OperationNotAllowed` — from
`web_fractal.core.security`. Map them to HTTP codes in the controller, never
deeper.
