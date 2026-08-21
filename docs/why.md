# Why web_fractal?

Every service that talks to SQLAlchemy ends up writing the same three things by
hand. `web_fractal` is what those three things look like when they are
declarations instead of code.

## 1. Filtering is not `if` statements

The version everyone writes first:

```python
query = select(User)
if name:
    query = query.where(User.name.ilike(f"%{name}%"))
if age_from:
    query = query.where(User.age >= age_from)
if role:
    query = query.where(User.role == role)
```

It grows one branch per field per endpoint, the Swagger page shows a bare
`dict`, and the enum coercion is copied around until one copy is wrong.

The declaration:

```python
class UserFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    role: FilterField[Role]
```

Operators come from the field type — `str` gets `ilike`, `int` gets `gte`, and
asking for `name__gte` is simply ignored rather than crashing. See
[Filters DSL](guide/filters.md).

## 2. Access control belongs in the query, not after it

Filtering rows in Python after they arrive is the bug that leaks data: someone
adds pagination, and now page 2 quietly contains rows the user may not see.

`ScopeBase` folds the rule into the same filter object *before* it becomes SQL:

```python
class EmployeeScope(ScopeBase):
    row_rule = RowRule(lambda ctx, m: m.org_id == ctx.user.organization_id)
    field_scopes = {"salary": FieldScope(visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles))}
```

See [Security (ABAC)](guide/security.md).

## 3. CRUD is not worth writing five times

`GenericRepo` implements create / get / filter / update / delete / count against
your model and DM class; `GenericService` adds `before_create` / `after_create`
hooks. Override a method when the domain actually differs — which is rarer than
it feels. See [CRUD mixins](guide/mixins.md).

## What it deliberately is not

**Not a framework.** No router, no settings object, no lifecycle, no opinions
about your project layout. Import one piece, ignore the rest.

**Not FastAPI-only.** The core imports neither FastAPI nor aiohttp: they live
behind extras, and `import web_fractal.db` costs you neither. HTTP is one
transport among Kafka, gRPC and GraphQL, all sharing
`ProtocolControllerABC`.

**Not a replacement for SQLAlchemy.** Filters produce ordinary `Select`
objects. Drop down to raw SQLAlchemy at any point and nothing breaks.

## Together with archtool

`web_fractal` pairs with [archtool](https://github.com/0nliner/archtool), which
wires dependencies by class annotations and enforces layer boundaries. Repos and
services declare what they need, archtool supplies it, and
`initialize_controllers_api` mounts the controllers.

Neither requires the other: `web_fractal` works without archtool, and archtool
works without `web_fractal`.
