# Anki Clone — web_fractal example

> A production-style Anki backend demonstrating every major web_fractal pattern.  
> Three domain modules. Zero `Depends(get_service)`. Full test suite.

---

## The problem this solves

```python
# ❌ The FastAPI DI trap — you've seen this everywhere
async def create_task(
    data: CreateTaskDTO,
    svc: TaskService = Depends(get_task_service),    # rebuilt every request
    uow: UnitOfWork  = Depends(get_uow),             # magic context manager
) -> TaskDM:
    ...
```

Service injection through `Depends()` was designed for request-scoped values
(auth tokens, per-request DB connections).  Stateless services don't need it.
They get rebuilt from scratch on every request, the factory functions
scatter state across module-level singletons, and testing requires
`app.dependency_overrides` gymnastics.

```python
# ✅ The web_fractal way — wired once at startup by archtool DI
class UsersController(AutoHttpController, UsersControllerABC):
    svc: UserServiceABC          # archtool resolves and injects at startup
    session_maker: ...           # set post-inject in bundle.py

    async def create_user(self, data: CreateUserDTO) -> UserDM:
        async with UnitOfWork(self.session_maker) as uow:   # per-request, explicit
            result = await self.svc.create([data.model_dump()], uow=uow)
            return result[0]
```

Services live as instance attributes.  `UnitOfWork` is an explicit async context
manager per request — you see every transaction boundary, no hidden commits.

---

## Project structure

```
app/
├── config.py                DATABASE_URL from environment
├── archtool_conf/
│   └── bundle.py            archtool DependencyInjector — repo → service → controller
├── entrypoints/
│   └── asgi.py              FastAPI app factory + lifespan
├── users/                   User domain module
│   ├── interfaces.py        ABCRepo / ABCService / ABCController declarations
│   ├── models.py            SQLAlchemy model
│   ├── dtos.py              Pydantic DTOs / Domain Model
│   ├── filters.py           FilterBase DSL declaration
│   ├── scopes.py            ABAC rules (email masking for non-admins)
│   ├── repos.py             GenericRepo — 5 lines for full CRUD
│   ├── services.py          GenericService — 2 lines
│   └── controllers.py       AutoHttpController — routes from method names
├── decks/                   Deck domain module (+ DeckScope row rule)
└── cards/                   Card domain + SM-2 spaced repetition
    ├── interfaces.py        Includes CardServiceABC.review() contract
    └── services.py          CardService.review() — domain logic outside controller
tests/
├── conftest.py              in-memory SQLite + archtool fixture
├── test_users.py            CRUD + FilterBase DSL query params
├── test_decks.py            CRUD + ABAC scope tests
└── test_cards.py            CRUD + SM-2 algorithm tests
```

---

## Quick start

```bash
# Install
pip install web_fractal fastapi uvicorn aiosqlite archtool

# Run
cd examples/anki
uvicorn app.entrypoints.asgi:app --reload

# Test
pytest tests/ -v
```

---

## Feature guide

### 1. archtool DI — the real wiring

[app/archtool_conf/bundle.py](app/archtool_conf/bundle.py):

```python
def build_injector(db_url="", *, session_maker=None):
    injector = DependencyInjector(
        modules_list=[AppModule("app.users"), AppModule("app.decks"), AppModule("app.cards")],
        project_root=_PROJECT_ROOT,
    )
    injector.inject()   # scans interfaces.py → repos.py/services.py/controllers.py, wires all

    # session_maker is outside project root — set manually after inject
    for instance in injector._dependencies.values():
        if isinstance(instance, (GenericRepo, HttpControllerABC)):
            instance.session_maker = session_maker

    return injector, engine
```

archtool scans each module's `interfaces.py` for abstract ABCs, finds their
concrete implementations, instantiates everything, and wires annotated dependencies.
One call — the full DI graph is assembled.

---

### 2. interfaces.py — the module contract

[app/users/interfaces.py](app/users/interfaces.py):

```python
class UserRepoABC(ABCRepo):
    @abstractmethod
    async def create(self, data: list[dict], *, uow) -> list: ...

class UserServiceABC(ABCService):
    @abstractmethod
    async def create(self, data: list[dict], *, uow) -> list: ...

class UsersControllerABC(ABCController):
    @abstractmethod
    def init_http_routes(self) -> None: ...
```

These ABCs are the **contracts** between layers. archtool reads them to discover
what to inject and where. Each module's repo/service/controller inherits from both
the module ABC and the web_fractal generic class.

**Why concrete class first in inheritance?** Python's MRO puts the concrete
`GenericRepo.create` before the abstract `UserRepoABC.create`, so `UserRepo`
is correctly non-abstract:
```python
class UserRepo(GenericRepo, UserRepoABC):   # GenericRepo first — covers the abstract
    model = User
    dm_class = UserDM
```

---

### 3. Zero-boilerplate CRUD — GenericRepo + GenericService

[app/users/repos.py](app/users/repos.py) — full CRUD in 4 lines:
```python
class UserRepo(GenericRepo, UserRepoABC):
    model = User
    dm_class = UserDM
```

[app/users/services.py](app/users/services.py) — delegation in 3 lines:
```python
class UserService(GenericService, UserServiceABC):
    repo: UserRepoABC  # archtool resolves this to UserRepo
```

`GenericRepo` provides `create / get / get_or_none / filter / update / delete / count`.
`GenericService` delegates all of them and exposes `before_create / after_create` hooks.

---

### 4. No FastAPI Depends for services

[app/users/controllers.py:32-36](app/users/controllers.py#L32)

`svc` and `session_maker` are **instance attributes**, set once by archtool in
[app/archtool_conf/bundle.py](app/archtool_conf/bundle.py).  Nothing in a method
signature is a FastAPI service dependency.

---

### 5. Explicit UnitOfWork per request

[app/users/controllers.py:40](app/users/controllers.py#L40)

```python
async with UnitOfWork(self.session_maker) as uow:
    result = await self.svc.create([data.model_dump()], uow=uow)
    return result[0]
# ↑ commits on success, rolls back on exception — visible in your code
```

Every mutable operation takes `uow` as an explicit keyword argument.
There are no hidden commits or auto-flush side effects.

---

### 6. FilterBase DSL — type-safe URL query params

[app/users/filters.py](app/users/filters.py) — declare once:
```python
class UserFilter(FilterBase):
    id:        FilterField[int]
    username:  FilterField[str]    # → ?username__ilike=ali, ?username__eq=alice
    email:     FilterField[str]
    role:      FilterField[str]
    is_active: FilterField[bool]
```

[app/users/controllers.py:52-70](app/users/controllers.py#L52) — use in controller:
```python
selection = UserFilter(
    username__ilike=username__ilike,
    role__eq=role__eq,
    order_by=order_by,
)
```

`apply_selection(query, User, selection)` translates this into a type-safe
SQLAlchemy `WHERE` clause.  Unsupported ops (e.g. `bool__gt`) are silently
ignored at parse time — no SQL injection vector.

---

### 7. ABAC Security Layer — ScopeBase

#### Field masking — [app/users/scopes.py](app/users/scopes.py)

```python
class UserScope(ScopeBase, strict=False):
    bypass_if = staticmethod(lambda ctx: ctx.user.extra.get("role") == "admin")
    field_scopes = {
        "email": FieldScope(visible=AccessRule(allow_if=lambda ctx: ctx.user.extra.get("role") == "admin"), mask_with="***@***"),
    }
```

Applied in [app/users/controllers.py:74-80](app/users/controllers.py#L74) — returns
users with masked email for non-admins.  No SQL changes needed — it's a pure
Python field replacement on the returned DM objects.

#### Row-level filtering — [app/decks/scopes.py:15](app/decks/scopes.py#L15)

```python
class DeckScope(ScopeBase, strict=False):
    row_rule = RowRule(
        condition=lambda ctx, m: or_(m.owner_id == ctx.user.id, m.is_public == True)
    )
```

`DeckScope.apply(selection, ctx)` adds a SQL `WHERE (owner_id = ?) OR (is_public = 1)`
to every filtered query.  The rule runs at the database layer — no Python-level
record filtering, no N+1, no data leaks.

#### Filter restriction — [app/decks/scopes.py:22](app/decks/scopes.py#L22)

`owner_id` filter expressions are stripped for non-admin users, preventing
enumeration of other users' private decks via `?owner_id__eq=<target>`.

Scope is applied in [app/decks/controllers.py:62-66](app/decks/controllers.py#L62)
when an `X-User-Id` header is present (simulates auth middleware).

Test: [tests/test_decks.py](tests/test_decks.py) — `test_scope_*` functions test
the scope logic directly as pure domain objects, no HTTP needed.

---

### 8. AutoHttpController — zero-boilerplate route registration

[app/users/controllers.py](app/users/controllers.py) and
[app/decks/controllers.py](app/decks/controllers.py):

Method name → HTTP method + path:

| Method name      | HTTP    | Path              |
|------------------|---------|-------------------|
| `create_user`    | POST    | `/users/`         |
| `get_user`       | GET     | `/users/{user_id}`|
| `filter_users`   | GET     | `/users/`         |
| `update_user`    | PATCH   | `/users/{user_id}`|
| `delete_user`    | DELETE  | `/users/{user_id}`|

Path parameters are inferred from scalar type annotations with no default value
(`user_id: int`).  Pydantic models become request bodies.  `Optional[T]` params
become query params.  No decorators, no `router.get(...)` calls.

---

### 9. Manual route registration when you need more control

[app/cards/controllers.py:39-48](app/cards/controllers.py#L39) — `review_card`
needs path `/{card_id}/review`, which `AutoHttpController` can't infer:

```python
def init_http_routes(self) -> None:
    self.reg_route(self.review_card, methods=["POST"], path="/{card_id}/review", response_model=CardDM)
    self.reg_route(self.get_card,    methods=["GET"],  path="/{card_id}",        response_model=CardDM)
    # ...
```

`HttpControllerABC.reg_route()` is the lower-level primitive.  Both styles
live in the same project; pick based on how standard your routes are.

---

### 10. Domain logic in the service layer

[app/cards/services.py:19-36](app/cards/services.py#L19) — SM-2 spaced repetition:

```python
def _sm2(card: CardDM, grade: int) -> dict:
    # grade < 3  → failed recall: reset interval=1, repetitions=0
    # grade >= 3 → increment repetitions, scale interval by ease_factor
    ...
```

`CardService.review()` calls `_sm2()` to compute the next review schedule,
then uses `CardFilter(id__eq=card_id)` + `repo.update()` to persist it.
All inside one `UnitOfWork` — the entire review operation is atomic.

---

### 11. DI Container — archtool DependencyInjector

[app/archtool_conf/bundle.py](app/archtool_conf/bundle.py):

```
interfaces.py declares ABCs (archtool reads these)
       ↓
repos.py / services.py / controllers.py contain concrete classes
       ↓
DependencyInjector.inject() discovers pairs, instantiates, wires
       ↓
bundle.py post-inject: sets session_maker on repos + controllers
       ↓
initialize_controllers_api(injector, app): init_http_routes() + app.include_router()
```

In tests: `build_injector(session_maker=test_session_maker)` — no overrides, no mocking.
Same wiring, different session_maker.

[tests/conftest.py](tests/conftest.py):
```python
async def client(session_maker):
    injector, _ = build_injector(session_maker=session_maker)
    app = FastAPI()
    initialize_controllers_api(injector, app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

---

## What you won't find here

| Anti-pattern | Why it's absent |
|---|---|
| `Depends(get_user_service)` | Services are stateless — wire once via archtool, not per-request |
| `Depends(get_uow)` | `UnitOfWork` is an explicit context manager in each handler |
| `app.dependency_overrides` in tests | Test build_injector() injects a real SQLite session_maker |
| Manual `Container._wire()` | archtool scans interfaces and wires automatically |
| SQL in controllers | All queries go through FilterBase → `apply_selection` |
| Business logic in controllers | SM-2 lives in `CardService`, not in the HTTP layer |
