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
      Опиши фильтр.<br>
      Опиши, кому что видно.<br>
      Запрос соберётся сам.
    </div>
  </div>
</div>

<p class="wf-credit"><span class="wf-credit-label">developed by</span><span class="wf-credit-sep">·</span><a class="wf-credit-name" href="https://github.com/0nliner" target="_blank">Чудайкин Александр</a><span class="wf-credit-sep">·</span><a class="wf-credit-org" href="https://github.com/0nliner" target="_blank">Бюро автоматизации процессов</a></p>

<p align="center">
  <a href="https://pypi.org/project/web-fractal"><img alt="PyPI" src="https://img.shields.io/pypi/v/web-fractal?color=2f8f8a"></a>
  <a href="https://pypi.org/project/web-fractal"><img alt="Python" src="https://img.shields.io/pypi/pyversions/web-fractal?color=2f8f8a"></a>
  <a href="https://github.com/0nliner/web_fractal/blob/master/LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-2f8f8a"></a>
</p>

**web_fractal** превращает три вещи, которые каждый сервис на SQLAlchemy пишет
заново — фильтрацию выборок, доступ на уровне строк и полей и рутину CRUD, — в
объявления.

```python
class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]

# FastAPI-зависимость с явными query-параметрами в Swagger
UserFilterDep = UserFilter.as_fastapi_dep()

@router.get("/users")
async def list_users(f: Annotated[UserFilter, Depends(UserFilterDep)], pag: Pagination = Depends()):
    return await repo.filter(EmployeeScope.apply(f, ctx), pag, uow=uow)
```

`?name__ilike=иван&age__gte=30&order_by=-age` превращается в типизированный
`WHERE`, а `EmployeeScope.apply` сужает его до того, что вызывающему разрешено
видеть, — ещё до того, как запрос уйдёт в базу.

## Установка

```bash
pip install web_fractal              # ядро
pip install "web_fractal[fastapi]"   # + HTTP-контроллеры и сборка приложения
```

Нужен Python 3.12+.

## Что внутри

| | |
|---|---|
| [DSL фильтров](guide/filters.md) | `FilterField[T]` → типизированные операторы, query-параметры, `WHERE` |
| [Права доступа (ABAC)](guide/security.md) | правила на строки, маскирование полей, ограничение операторов |
| [CRUD-миксины](guide/mixins.md) | `GenericRepo` / `GenericService` — create, filter, update, delete, count |
| [Единица работы](guide/unit_of_work.md) | одна сессия на операцию, явный commit |
| [HTTP-контроллеры](guide/http.md) | ручная регистрация или маршруты из имён методов |
| [Транспорты](guide/transports.md) | тот же контроллер для Kafka, gRPC, GraphQL |
| [CLI](guide/cli.md) | `wf init`, `add-module`, `validate`, `graph`, `diagram`, `extract` |

## Это не фреймворк

`web_fractal` не владеет вашим приложением. У него нет своего роутера, объекта
настроек и жизненного цикла. Каждая часть работает отдельно: можно взять
фильтры и оставить свои репозитории — или взять миксины и оставить свой слой
запросов.

FastAPI-часть спрятана за экстру: ядро вообще не импортирует веб-фреймворк.
Подробнее — [Зачем web_fractal?](why.md).
