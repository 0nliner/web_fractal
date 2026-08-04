"""
FilterBase DSL — standalone demo.
Run:  python examples/demo_filters.py

Shows:
  - field__op=value parsing
  - type coercion (str, int, float, Enum, UUID)
  - in_ / is_null semantics
  - op validation (invalid op for type is silently dropped)
  - OrderBy
  - as_fastapi_dep() signature inspection
  - apply_selection against in-memory SQLite
"""
import asyncio
import inspect
import uuid
from enum import Enum

from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from web_fractal.filters import FilterBase, FilterField, Op, OrderBy, apply_selection


# ─── Domain model ────────────────────────────────────────────────────────────

class Priority(Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


class TaskBase(DeclarativeBase): pass


class Task(TaskBase):
    __tablename__ = "tasks"
    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title:    Mapped[str] = mapped_column(String(200))
    status:   Mapped[str] = mapped_column(String(50))
    score:    Mapped[int] = mapped_column(Integer, default=0)


class TaskFilter(FilterBase):
    title:  FilterField[str]
    status: FilterField[Priority]
    score:  FilterField[int]


# ─── Demo helpers ─────────────────────────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def show(label: str, value) -> None:
    print(f"  {label:<38} {value!r}")


# ─── Demo 1: parsing & coercion ───────────────────────────────────────────────

def demo_parsing():
    section("1. Parsing & type coercion")

    f = TaskFilter(
        title__ilike="%report%",
        score__gte="42",        # string → int
        status__eq="high",      # string → Priority.high
        status__in_="low,high", # comma-sep → [Priority.low, Priority.high]
    )
    for expr in f.active_expressions:
        show(f"{expr.field_name}__{expr.op.value}", expr.value)

    section("  op invalid for type → silently dropped")
    f2 = TaskFilter(title__gt="foo")  # gt not valid for str
    show("active_expressions (should be [])", f2.active_expressions)

    section("  is_null coercion")
    for raw in ("true", "1", "yes", "false", "0"):
        f3 = TaskFilter(title__is_null=raw)
        show(f"title__is_null={raw!r}", f3.active_expressions[0].value)


# ─── Demo 2: OrderBy ─────────────────────────────────────────────────────────

def demo_order_by():
    section("2. OrderBy — prefix '-' = DESC")
    for spec in ("score", "-score", "title", "-title"):
        ob = OrderBy(spec)
        show(f"OrderBy({spec!r})", f"field={ob.field}, asc={ob.ascending}")

    f = TaskFilter(order_by="-score")
    show("filter.order_by", f.order_by)


# ─── Demo 3: UUID support ─────────────────────────────────────────────────────

def demo_uuid():
    section("3. UUID support")

    class UUIDFilter(FilterBase):
        import uuid as _uuid
        uid: FilterField[_uuid.UUID]

    u1, u2 = uuid.uuid4(), uuid.uuid4()
    f = UUIDFilter(uid__in_=f"{u1},{u2}")
    result = f.active_expressions[0].value
    show("in_ coerced to list[UUID]", [str(v) for v in result])
    assert all(isinstance(v, uuid.UUID) for v in result)
    print("  ✓ all items are uuid.UUID instances")


# ─── Demo 4: as_fastapi_dep signature ────────────────────────────────────────

def demo_fastapi_dep():
    section("4. as_fastapi_dep() — generated Query parameters")
    dep = TaskFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    print(f"  Function: {dep.__name__}")
    print(f"  Parameters ({len(sig.parameters)}):")
    for name, param in sig.parameters.items():
        ann = getattr(param.annotation, "__name__", str(param.annotation))
        print(f"    {name:<30} : {ann}")

    # Verify str field gets no gt/lt
    params = set(sig.parameters)
    assert "title__gt" not in params,  "title__gt must not appear (invalid for str)"
    assert "title__ilike" in params,   "title__ilike must appear"
    assert "score__gt" in params,      "score__gt must appear (valid for int)"
    assert "status__eq" in params,     "status__eq must appear (Enum)"
    assert "status__gt" not in params, "status__gt must not appear (Enum has no gt)"
    print("  ✓ only type-valid ops generated")

    # Build an instance via dep (as FastAPI would)
    instance = dep(title__ilike="%api%", score__gte=10)
    print(f"\n  dep(title__ilike='%api%', score__gte=10) → {instance}")


# ─── Demo 5: apply_selection against SQLite ──────────────────────────────────

async def demo_apply_selection():
    section("5. apply_selection against in-memory SQLite")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TaskBase.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)

    # Seed data
    async with maker() as session:
        session.add_all([
            Task(title="Write API report",  status="high",   score=80),
            Task(title="Fix login bug",     status="medium", score=55),
            Task(title="Write unit tests",  status="low",    score=30),
            Task(title="Deploy to staging", status="high",   score=90),
            Task(title="Code review",       status="medium", score=70),
        ])
        await session.commit()

    async def run_filter(label: str, f: TaskFilter):
        q = apply_selection(select(Task), Task, f)
        async with maker() as session:
            rows = (await session.execute(q)).scalars().all()
        print(f"\n  [{label}] → {len(rows)} row(s)")
        for r in rows:
            print(f"    #{r.id}  score={r.score:<4}  {r.title}")

    await run_filter("all",                    TaskFilter())
    await run_filter("score__gte=70",          TaskFilter(score__gte=70))
    await run_filter("title__ilike='%write%'", TaskFilter(title__ilike="%write%"))
    await run_filter("status__in_=high,medium",TaskFilter(status__in_="high,medium"))
    await run_filter("score__gte=60, ASC",     TaskFilter(score__gte=60, order_by="score"))
    await run_filter("score__gte=60, DESC",    TaskFilter(score__gte=60, order_by="-score"))

    await engine.dispose()


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo_parsing()
    demo_order_by()
    demo_uuid()
    demo_fastapi_dep()
    asyncio.run(demo_apply_selection())
    print("\n\n✓ All filter demos passed.\n")
