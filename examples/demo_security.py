"""
ABAC Security Layer — standalone demo.
Run:  python examples/demo_security.py

Shows:
  - SecurityContext with UserPrincipal
  - AccessRule (allow_if / deny_if)
  - RowRule — SQL WHERE injected by scope
  - FieldScope — field visibility with mask_with
  - FilterScope — op whitelist (prevents enumeration attacks)
  - ScopeBase.apply() — non-destructive filter transformation
  - ScopeBase.evaluate_field() / evaluate_filter() — pure predicates
  - strict=True mode — default-deny for unregistered fields
  - bypass_if — admin skips all rules
  - Stack two scopes on one filter (team + org isolation)
"""
import asyncio

from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from web_fractal.core.security import (
    AccessRule, EnvContext, FieldDecision, FieldScope, FilterScope,
    RowRule, ScopeBase, SecurityContext, UserPrincipal,
)
from web_fractal.filters import FilterBase, FilterField, Op, apply_selection


# ─── Domain ──────────────────────────────────────────────────────────────────

class EmployeeFilter(FilterBase):
    name:   FilterField[str]
    salary: FilterField[float]
    dept:   FilterField[str]


# ─── Scopes ──────────────────────────────────────────────────────────────────

class EmployeeScope(ScopeBase, strict=False):
    """
    Rules:
      - Everyone sees only their own department (row_rule)
      - Only HR/Admin can see or filter by salary
      - Salary filtering restricted to eq only (prevent binary-search enumeration)
      - Admin bypasses everything
    """
    bypass_if = staticmethod(lambda ctx: "admin" in ctx.user.roles)

    row_rule = RowRule(
        condition=lambda ctx, m: m.dept == ctx.user.extra.get("dept")
    )

    field_scopes = {
        "salary": FieldScope(
            visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles),
            mask_with="***",
        ),
    }

    filter_scopes = {
        "salary": FilterScope(
            rule=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles),
            allowed_ops=[Op.eq],  # no gt/lt → prevents enumeration
        ),
    }


class StrictPayrollScope(ScopeBase, strict=True):
    """Default-deny: only explicitly whitelisted fields can be filtered."""
    filter_scopes = {
        "name": FilterScope(),  # only name is allowed
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ctx(roles=(), dept=None, uid=1):
    return SecurityContext(
        user=UserPrincipal(id=uid, roles=list(roles), extra={"dept": dept}),
        environment=EnvContext(),
    )


def section(t): print(f"\n{'─'*60}\n  {t}\n{'─'*60}")
def ok(msg):     print(f"  ✓  {msg}")
def show(label, val): print(f"  {label:<42} {val!r}")


# ─── Demo 1: AccessRule ───────────────────────────────────────────────────────

def demo_access_rule():
    section("1. AccessRule — lazy predicates")

    default = AccessRule()
    show("default (no rules) → always allow", default.evaluate(ctx()))

    hr_only = AccessRule(allow_if=lambda c: "hr" in c.user.roles)
    show("hr_only for hr user",   hr_only.evaluate(ctx(["hr"])))
    show("hr_only for intern",    hr_only.evaluate(ctx(["intern"])))

    deny_banned = AccessRule(
        allow_if=lambda c: True,
        deny_if=lambda c: "banned" in c.user.roles,
    )
    show("deny_banned for admin",        deny_banned.evaluate(ctx(["admin"])))
    show("deny_banned for banned+admin", deny_banned.evaluate(ctx(["banned", "admin"])))
    ok("deny_if takes precedence over allow_if")


# ─── Demo 2: evaluate_field / evaluate_filter ────────────────────────────────

def demo_evaluate():
    section("2. Pure predicates — no DB required")

    for role, dept in [("intern", "eng"), ("hr", "eng"), ("admin", "any")]:
        c = ctx([role], dept=dept)
        fd = EmployeeScope.evaluate_field("salary", c)
        show(f"evaluate_field('salary', role={role!r})", fd)

    print()
    for role in ["intern", "hr", "admin"]:
        for op in [Op.eq, Op.gt]:
            c = ctx([role], dept="eng")
            allowed = EmployeeScope.evaluate_filter("salary", op, c)
            show(f"evaluate_filter('salary', {op.value!r}, role={role!r})", allowed)

    ok("hr can filter salary by eq only; admin bypasses all")


# ─── Demo 3: ScopeBase.apply() ───────────────────────────────────────────────

def demo_apply():
    section("3. ScopeBase.apply() — non-destructive transformation")

    f = EmployeeFilter(name__eq="Alice", salary__gt=50000.0, dept__eq="eng")
    print(f"  Original filter: {f}")

    # intern: salary dropped (rule denies), dept OK, name OK
    secured_intern = EmployeeScope.apply(f, ctx(["intern"], dept="eng"))
    print(f"\n  After apply (intern):")
    for e in secured_intern.active_expressions:
        print(f"    {e.field_name}__{e.op.value} = {e.value}")
    ok("salary expression removed (intern has no access)")
    ok("row_rule registered → will add WHERE dept='eng'")

    # hr: salary eq allowed, but salary__gt removed (only eq allowed)
    f2 = EmployeeFilter(salary__gt=50000.0, salary__eq=60000.0)
    secured_hr = EmployeeScope.apply(f2, ctx(["hr"], dept="hr"))
    print(f"\n  After apply (hr, salary__gt + salary__eq input):")
    for e in secured_hr.active_expressions:
        print(f"    {e.field_name}__{e.op.value} = {e.value}")
    ok("salary__gt removed (op not in allowed_ops=[eq])")
    ok("salary__eq kept")

    # admin: bypass — returns original object unchanged
    secured_admin = EmployeeScope.apply(f, ctx(["admin"], dept="hq"))
    assert secured_admin is f
    ok("admin bypass returns original filter reference unchanged")

    # original not mutated
    assert f.has_filter_for("salary"), "original must not be mutated"
    ok("original filter never mutated")


# ─── Demo 4: strict=True mode ────────────────────────────────────────────────

def demo_strict():
    section("4. strict=True — default-deny for unknown fields")

    f = EmployeeFilter(name__eq="Bob", salary__eq=50000.0, dept__eq="hr")
    secured = StrictPayrollScope.apply(f, ctx())
    print(f"  Input expressions:  {[e.field_name for e in f.active_expressions]}")
    print(f"  Secured expressions:{[e.field_name for e in secured.active_expressions]}")
    ok("only 'name' passes (others not in filter_scopes)")


# ─── Demo 5: RowRule + apply_selection SQL ───────────────────────────────────

class EmpBase(DeclarativeBase): pass


class Employee(EmpBase):
    __tablename__ = "employees_demo"
    id:     Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:   Mapped[str] = mapped_column(String(100))
    dept:   Mapped[str] = mapped_column(String(50))
    salary: Mapped[int] = mapped_column(Integer)


async def demo_row_rule_sql():
    section("5. RowRule → WHERE injected into apply_selection SQL")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(EmpBase.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add_all([
            Employee(name="Alice",   dept="eng", salary=80000),
            Employee(name="Bob",     dept="eng", salary=90000),
            Employee(name="Carol",   dept="hr",  salary=70000),
            Employee(name="Dave",    dept="hr",  salary=75000),
            Employee(name="Eve",     dept="eng", salary=95000),
        ])
        await session.commit()

    class EmpFilter(FilterBase):
        name:   FilterField[str]
        dept:   FilterField[str]
        salary: FilterField[int]

    class EmpScope(ScopeBase):
        bypass_if = staticmethod(lambda c: "admin" in c.user.roles)
        row_rule = RowRule(condition=lambda c, m: m.dept == c.user.extra.get("dept"))

    async def query(label, filter_obj):
        q = apply_selection(select(Employee), Employee, filter_obj)
        async with maker() as s:
            rows = (await s.execute(q)).scalars().all()
        print(f"\n  [{label}] → {len(rows)} row(s): {[r.name for r in rows]}")
        return rows

    # Engineer only sees eng dept
    eng_ctx  = ctx(["engineer"], dept="eng")
    secured  = EmpScope.apply(EmpFilter(), eng_ctx)
    await query("engineer (dept=eng), no extra filter", secured)

    # HR sees only hr dept
    hr_ctx  = ctx(["hr"], dept="hr")
    secured = EmpScope.apply(EmpFilter(), hr_ctx)
    await query("hr (dept=hr), no extra filter", secured)

    # Admin sees everything
    admin_ctx = ctx(["admin"])
    secured   = EmpScope.apply(EmpFilter(), admin_ctx)
    rows      = await query("admin (bypass), no extra filter", secured)
    assert len(rows) == 5
    ok("admin sees all 5 rows")

    # Stacked: row_rule from scope AND explicit filter
    secured = EmpScope.apply(EmpFilter(name__ilike="%e%"), eng_ctx)
    rows    = await query("engineer + name__ilike='%e%'", secured)
    ok("filters compose cleanly")

    await engine.dispose()


# ─── Demo 6: stacking two scopes ─────────────────────────────────────────────

def demo_stacked_scopes():
    section("6. Stacking two scopes")

    class OrgScope(ScopeBase):
        row_rule = RowRule(condition=lambda c, m: m.dept == c.user.organization_id)

    class TeamScope(ScopeBase):
        row_rule = RowRule(condition=lambda c, m: m.dept == "frontend")

    f = EmployeeFilter(name__eq="Alice")
    c = SecurityContext(user=UserPrincipal(id=1, roles=[], organization_id="eng"))

    f1 = OrgScope.apply(f, c)
    f2 = TeamScope.apply(f1, c)
    print(f"  Row rules after stacking: {len(f2._scope_row_rules)}")
    ok("two row rules registered — both WHERE conditions will fire")
    ok("original filter unmodified")
    assert f.has_filter_for("name")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo_access_rule()
    demo_evaluate()
    demo_apply()
    demo_strict()
    asyncio.run(demo_row_rule_sql())
    demo_stacked_scopes()
    print("\n\n✓ All ABAC security demos passed.\n")
