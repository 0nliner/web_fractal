---
title: web_fractal
---

<div class="wf-banner">
  <div class="wf-banner-glow"></div>
  <div class="wf-banner-icon">
    <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="28" y="6" width="24" height="24" rx="5" fill="#2f8f8a"/>
      <rect x="6"  y="46" width="24" height="24" rx="5" fill="#2f8f8a" opacity="0.85"/>
      <rect x="50" y="46" width="24" height="24" rx="5" fill="#2f8f8a" opacity="0.85"/>
      <line x1="34" y1="30" x2="20" y2="46" stroke="#2f8f8a" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="46" y1="30" x2="60" y2="46" stroke="#2f8f8a" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="30" y1="58" x2="50" y2="58" stroke="#2f8f8a" stroke-width="2.5" stroke-linecap="round"/>
      <rect x="34" y="12" width="12" height="12" rx="2.5" fill="#0f1514"/>
      <rect x="12" y="52" width="12" height="12" rx="2.5" fill="#0f1514"/>
      <rect x="56" y="52" width="12" height="12" rx="2.5" fill="#0f1514"/>
      <rect x="37" y="15" width="6" height="6" rx="1.2" fill="#2f8f8a"/>
      <rect x="15" y="55" width="6" height="6" rx="1.2" fill="#2f8f8a"/>
      <rect x="59" y="55" width="6" height="6" rx="1.2" fill="#2f8f8a"/>
    </svg>
  </div>
  <div>
    <div class="wf-banner-title">web_fractal</div>
    <div class="wf-banner-tagline">
      Declare the filter.<br>
      Declare who may see what.<br>
      The query writes itself.
    </div>
  </div>
</div>

<p class="wf-credit"><span class="wf-credit-label">developed by</span><span class="wf-credit-sep">·</span><a class="wf-credit-name" href="https://github.com/0nliner" target="_blank">Чудайкин Александр</a><span class="wf-credit-sep">·</span><a class="wf-credit-org" href="https://github.com/0nliner" target="_blank">Бюро автоматизации процессов</a></p>

<p align="center">
  <a href="https://pypi.org/project/web-fractal"><img alt="PyPI" src="https://img.shields.io/pypi/v/web-fractal?color=2f8f8a"></a>
  <a href="https://pypi.org/project/web-fractal"><img alt="Python" src="https://img.shields.io/pypi/pyversions/web-fractal?color=2f8f8a"></a>
  <a href="https://github.com/0nliner/web_fractal/blob/master/LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-2f8f8a"></a>
</p>

**web_fractal** turns three things every SQLAlchemy service rewrites by hand —
query filtering, row/field-level access, and CRUD plumbing — into declarations.

```python
class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]

# FastAPI dependency with explicit query params in Swagger
UserFilterDep = UserFilter.as_fastapi_dep()

@router.get("/users")
async def list_users(f: Annotated[UserFilter, Depends(UserFilterDep)], pag: Pagination = Depends()):
    return await repo.filter(EmployeeScope.apply(f, ctx), pag, uow=uow)
```

`?name__ilike=иван&age__gte=30&order_by=-age` becomes a typed `WHERE`, and
`EmployeeScope.apply` narrows it to what the caller is allowed to see — before
the query reaches the database.

## Install

```bash
pip install web_fractal              # core
pip install "web_fractal[fastapi]"   # + HTTP controllers and app assembly
```

Requires Python 3.12+.

## What it gives you

| | |
|---|---|
| [Filters DSL](guide/filters.md) | `FilterField[T]` → typed operators, query params, `WHERE` |
| [Security (ABAC)](guide/security.md) | row rules, field masking, per-field operator limits |
| [CRUD mixins](guide/mixins.md) | `GenericRepo` / `GenericService` — create, filter, update, delete, count |
| [Unit of Work](guide/unit_of_work.md) | one session per operation, explicit commit |
| [HTTP controllers](guide/http.md) | manual `reg_route` or routes derived from method names |
| [Transports](guide/transports.md) | the same controller shape for Kafka, gRPC, GraphQL |
| [CLI](guide/cli.md) | `wf init`, `add-module`, `validate`, `graph`, `diagram`, `extract` |

## Not a framework

`web_fractal` does not own your app. It has no router of its own, no settings
object, no lifecycle. Every piece is usable alone: take the filters and keep
your repositories, or take the mixins and keep your own query layer.

The FastAPI parts live behind an extra — the core does not import a web
framework at all. See [Why web_fractal?](why.md).
