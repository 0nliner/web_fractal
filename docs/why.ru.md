# Зачем web_fractal?

Каждый сервис, который ходит в SQLAlchemy, рано или поздно пишет руками одни и
те же три вещи. `web_fractal` — это те же три вещи, но объявлениями вместо кода.

## 1. Фильтрация — это не цепочка `if`

Версия, которую пишут первой:

```python
query = select(User)
if name:
    query = query.where(User.name.ilike(f"%{name}%"))
if age_from:
    query = query.where(User.age >= age_from)
if role:
    query = query.where(User.role == role)
```

Она растёт на одну ветку с каждым полем и каждой ручкой, в Swagger вместо
параметров виден голый `dict`, а приведение enum копируется по файлам, пока одна
из копий не разойдётся с остальными.

Объявление:

```python
class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    role: FilterField[Role]
```

Операторы берутся из типа поля: у `str` есть `ilike`, у `int` — `gte`, а запрос
`name__gte` просто игнорируется, а не роняет ручку. Подробнее —
[DSL фильтров](guide/filters.md).

## 2. Права должны попадать в запрос, а не применяться после него

Отфильтровать строки в Python после того, как они пришли, — это та самая утечка:
кто-нибудь добавляет пагинацию, и на второй странице тихо оказываются записи,
которых пользователь видеть не должен.

`ScopeBase` вкладывает правило в тот же объект фильтра **до** того, как он
станет SQL:

```python
class EmployeeScope(ScopeBase):
    row_rule = RowRule(lambda ctx, m: m.org_id == ctx.user.organization_id)
    field_scopes = {"salary": FieldScope(visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles))}
```

Подробнее — [Права доступа (ABAC)](guide/security.md).

## 3. CRUD не стоит писать пять раз

`GenericRepo` реализует create / get / filter / update / delete / count поверх
вашей модели и DM-класса; `GenericService` добавляет хуки `before_create` и
`after_create`. Метод переопределяется там, где домен действительно отличается,
— а это реже, чем кажется. Подробнее — [CRUD-миксины](guide/mixins.md).

## Чем библиотека сознательно не является

**Не фреймворк.** Ни роутера, ни объекта настроек, ни жизненного цикла, ни
мнения о раскладке вашего проекта. Импортируйте одну часть, остальное не
трогайте.

**Не только FastAPI.** Ядро не импортирует ни FastAPI, ни aiohttp: они за
экстрами, и `import web_fractal.db` не тянет ни того, ни другого. HTTP —
один транспорт из нескольких: рядом Kafka, gRPC и GraphQL с общим
`ProtocolControllerABC`.

**Не замена SQLAlchemy.** Фильтры отдают обычный `Select`. В любой момент можно
спуститься к чистому SQLAlchemy, и ничего не сломается.

## Вместе с archtool

`web_fractal` дружит с [archtool](https://github.com/0nliner/archtool): тот
разводит зависимости по классовым аннотациям и следит за границами слоёв. Репо
и сервисы объявляют, что им нужно, archtool это подставляет, а
`initialize_controllers_api` монтирует контроллеры.

Друг без друга они работают: `web_fractal` живёт без archtool, archtool — без
`web_fractal`.
