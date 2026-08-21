# Права доступа (ABAC)

Доступ по атрибутам, который вкладывается в фильтр **до** того, как тот станет
SQL. Ничего не отсеивается в Python после того, как строки уже пришли: именно
этот приём начинает течь в тот день, когда кто-нибудь добавит пагинацию.

## Контекст

```python
from web_fractal.core.security import SecurityContext, UserPrincipal, EnvContext

ctx = SecurityContext(
    user=UserPrincipal(id=42, roles=["hr"], organization_id=7),
    environment=EnvContext(ip="10.0.0.1", tenant="acme"),
)
```

## Скоуп

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

| Объявление | Что делает |
|---|---|
| `bypass_if` | замыкает весь скоуп — та самая админская лазейка |
| `row_rule` | условие, дописываемое в запрос: какие строки вообще существуют |
| `field_scopes` | видно ли поле и чем его подменять |
| `filter_scopes` | какими операторами по полю разрешено фильтровать |

`strict=True` запрещает всё, что не разрешено явно; по умолчанию режим мягкий.

## Применение

```python
secured = EmployeeScope.apply(employee_filter, ctx)   # -> FilterBase
rows = await repo.filter(secured, pag, uow=uow)
```

`apply` возвращает тот же объект фильтра с добавленным правилом на строки и
выброшенными выражениями по запрещённым операторам.

## Решения по полям

```python
decision = EmployeeScope.evaluate_field("salary", ctx)
decision.visible      # bool
decision.mask_with    # чем подменить, если скрыто
```

Пригодится при сериализации: скрытое поле становится `mask_with`, а не
исчезает, — форма ответа для клиента остаётся стабильной.

```python
EmployeeScope.evaluate_filter("salary", Op.gt, ctx)   # False → перебор закрыт
```

Ради этого `filter_scopes` и существует: поле может быть **невидимым** ни для
кого и всё равно утекать через двоичный поиск `salary__gt=100000`, если
операторы не ограничены.

## Исключения

`AccessDenied`, `FieldNotVisible`, `OperationNotAllowed` — из
`web_fractal.core.security`. Превращайте их в HTTP-коды в контроллере и нигде
глубже.
