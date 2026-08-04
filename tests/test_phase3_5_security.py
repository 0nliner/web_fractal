"""
Phase 3.5 tests: ABAC Security Layer
- SecurityContext / UserPrincipal
- AccessRule (allow_if, deny_if, default allow)
- RowRule (condition callable)
- FieldScope (visibility)
- FilterScope (allowed_ops, rule)
- ScopeBase.apply() — expression filtering, row_rule registration, bypass, strict mode
- ScopeBase.evaluate_field() / evaluate_filter() — pure predicates, no DB
- apply_selection integration with _scope_row_rules
"""
import pytest
import pytest_asyncio
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from web_fractal.filters import FilterBase, FilterField, Op, ParsedExpression, apply_selection
from web_fractal.core.security.context import EnvContext, SecurityContext, UserPrincipal
from web_fractal.core.security.exceptions import AccessDenied, FieldNotVisible, OperationNotAllowed
from web_fractal.core.security.rules import AccessRule, FieldScope, FilterScope, RowRule
from web_fractal.core.security.scope import FieldDecision, ScopeBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ctx(roles: list[str] = None, org_id=None) -> SecurityContext:
    return SecurityContext(user=UserPrincipal(id=1, roles=roles or [], organization_id=org_id))


class EmpFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    salary: FilterField[float]
    department: FilterField[str]


# ---------------------------------------------------------------------------
# SecurityContext / UserPrincipal
# ---------------------------------------------------------------------------

def test_security_context_creates():
    ctx = SecurityContext(user=UserPrincipal(id=42, roles=["admin"]))
    assert ctx.user.id == 42
    assert "admin" in ctx.user.roles


def test_user_principal_defaults():
    u = UserPrincipal()
    assert u.roles == []
    assert u.organization_id is None
    assert u.extra == {}


def test_env_context_defaults():
    env = EnvContext()
    assert env.ip is None
    assert env.tenant is None


@pytest.mark.asyncio
async def test_security_context_build():
    user = UserPrincipal(id=99, roles=["user"])
    ctx = await SecurityContext.build(user)
    assert ctx.user is user


# ---------------------------------------------------------------------------
# AccessRule
# ---------------------------------------------------------------------------

def test_access_rule_default_allow():
    rule = AccessRule()
    ctx = make_ctx()
    assert rule.evaluate(ctx) is True


def test_access_rule_allow_if_true():
    rule = AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles)
    assert rule.evaluate(make_ctx(["hr"])) is True
    assert rule.evaluate(make_ctx(["user"])) is False


def test_access_rule_deny_if_takes_precedence():
    rule = AccessRule(
        allow_if=lambda ctx: True,
        deny_if=lambda ctx: "banned" in ctx.user.roles,
    )
    assert rule.evaluate(make_ctx(["admin"])) is True
    assert rule.evaluate(make_ctx(["banned", "admin"])) is False


def test_access_rule_deny_if_only():
    rule = AccessRule(deny_if=lambda ctx: ctx.user.id == 0)
    assert rule.evaluate(make_ctx()) is True
    ctx_zero = SecurityContext(user=UserPrincipal(id=0))
    assert rule.evaluate(ctx_zero) is False


# ---------------------------------------------------------------------------
# RowRule
# ---------------------------------------------------------------------------

def test_row_rule_build():
    class FakeModel:
        org_id = "col_placeholder"

    rule = RowRule(condition=lambda ctx, m: (m.org_id, ctx.user.organization_id))
    ctx = make_ctx(org_id=5)
    result = rule.build(ctx, FakeModel)
    assert result == ("col_placeholder", 5)


# ---------------------------------------------------------------------------
# FieldScope
# ---------------------------------------------------------------------------

def test_field_scope_default_visible():
    scope = FieldScope()
    assert scope.visible.evaluate(make_ctx()) is True
    assert scope.mask_with is None


def test_field_scope_restricted():
    scope = FieldScope(
        visible=AccessRule(allow_if=lambda ctx: "admin" in ctx.user.roles),
        mask_with="***",
    )
    assert scope.visible.evaluate(make_ctx(["admin"])) is True
    assert scope.visible.evaluate(make_ctx(["user"])) is False
    assert scope.mask_with == "***"


# ---------------------------------------------------------------------------
# FilterScope
# ---------------------------------------------------------------------------

def test_filter_scope_default_allows_all():
    scope = FilterScope()
    assert scope.rule.evaluate(make_ctx()) is True
    assert scope.allowed_ops is None


def test_filter_scope_restricts_ops():
    scope = FilterScope(allowed_ops=[Op.eq])
    assert scope.allowed_ops == [Op.eq]


def test_filter_scope_rule_blocks():
    scope = FilterScope(rule=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles))
    assert scope.rule.evaluate(make_ctx(["hr"])) is True
    assert scope.rule.evaluate(make_ctx(["user"])) is False


# ---------------------------------------------------------------------------
# ScopeBase — basic structure
# ---------------------------------------------------------------------------

class BasicScope(ScopeBase):
    filter_scopes = {
        "salary": FilterScope(
            rule=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles),
            allowed_ops=[Op.eq, Op.gt],
        ),
    }
    field_scopes = {
        "salary": FieldScope(
            visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles),
            mask_with=None,
        ),
    }


def test_scope_subclass_has_own_dicts():
    class ScopeA(ScopeBase):
        filter_scopes = {"a": FilterScope()}

    class ScopeB(ScopeBase):
        filter_scopes = {"b": FilterScope()}

    assert "a" in ScopeA.filter_scopes
    assert "b" not in ScopeA.filter_scopes
    assert "b" in ScopeB.filter_scopes


def test_strict_mode_flag():
    class StrictScope(ScopeBase, strict=True):
        pass

    class LaxScope(ScopeBase, strict=False):
        pass

    assert StrictScope._strict is True
    assert LaxScope._strict is False


# ---------------------------------------------------------------------------
# evaluate_field
# ---------------------------------------------------------------------------

def test_evaluate_field_visible():
    decision = BasicScope.evaluate_field("salary", make_ctx(["hr"]))
    assert decision.visible is True


def test_evaluate_field_not_visible():
    decision = BasicScope.evaluate_field("salary", make_ctx(["user"]))
    assert decision.visible is False


def test_evaluate_field_unknown_field_lax_mode():
    decision = BasicScope.evaluate_field("name", make_ctx())
    assert decision.visible is True


def test_evaluate_field_unknown_field_strict_mode():
    class Strict(ScopeBase, strict=True):
        field_scopes = {"salary": FieldScope()}

    decision = Strict.evaluate_field("name", make_ctx())
    assert decision.visible is False


def test_evaluate_field_bypass():
    class AdminScope(ScopeBase):
        bypass_if = staticmethod(lambda ctx: "admin" in ctx.user.roles)
        field_scopes = {
            "salary": FieldScope(visible=AccessRule(allow_if=lambda ctx: False))
        }

    assert AdminScope.evaluate_field("salary", make_ctx(["admin"])).visible is True
    assert AdminScope.evaluate_field("salary", make_ctx(["user"])).visible is False


def test_evaluate_field_mask_with_propagated():
    class MaskedScope(ScopeBase):
        field_scopes = {
            "ssn": FieldScope(
                visible=AccessRule(allow_if=lambda ctx: False),
                mask_with="REDACTED",
            )
        }

    decision = MaskedScope.evaluate_field("ssn", make_ctx())
    assert decision.visible is False
    assert decision.mask_with == "REDACTED"


# ---------------------------------------------------------------------------
# evaluate_filter
# ---------------------------------------------------------------------------

def test_evaluate_filter_allowed():
    assert BasicScope.evaluate_filter("salary", Op.eq, make_ctx(["hr"])) is True
    assert BasicScope.evaluate_filter("salary", Op.gt, make_ctx(["hr"])) is True


def test_evaluate_filter_denied_by_rule():
    assert BasicScope.evaluate_filter("salary", Op.eq, make_ctx(["user"])) is False


def test_evaluate_filter_denied_by_op():
    # hr can filter salary but only eq/gt — not ilike
    assert BasicScope.evaluate_filter("salary", Op.ilike, make_ctx(["hr"])) is False


def test_evaluate_filter_unknown_field_lax():
    assert BasicScope.evaluate_filter("name", Op.eq, make_ctx()) is True


def test_evaluate_filter_unknown_field_strict():
    class Strict(ScopeBase, strict=True):
        filter_scopes = {"salary": FilterScope()}

    assert Strict.evaluate_filter("name", Op.eq, make_ctx()) is False
    assert Strict.evaluate_filter("salary", Op.eq, make_ctx()) is True


def test_evaluate_filter_bypass():
    class AdminScope(ScopeBase):
        bypass_if = staticmethod(lambda ctx: "admin" in ctx.user.roles)
        filter_scopes = {
            "salary": FilterScope(
                rule=AccessRule(allow_if=lambda ctx: False),
                allowed_ops=[Op.eq],
            )
        }

    assert AdminScope.evaluate_filter("salary", Op.gt, make_ctx(["admin"])) is True
    assert AdminScope.evaluate_filter("salary", Op.gt, make_ctx(["user"])) is False


# ---------------------------------------------------------------------------
# ScopeBase.apply()
# ---------------------------------------------------------------------------

def test_apply_removes_denied_field():
    f = EmpFilter(salary__eq=1000.0, name__eq="Alice")
    secured = BasicScope.apply(f, make_ctx(["user"]))
    assert not secured.has_filter_for("salary")
    assert secured.has_filter_for("name")


def test_apply_keeps_allowed_field():
    f = EmpFilter(salary__eq=1000.0, name__eq="Alice")
    secured = BasicScope.apply(f, make_ctx(["hr"]))
    assert secured.has_filter_for("salary")
    assert secured.has_filter_for("name")


def test_apply_removes_disallowed_op():
    f = EmpFilter(salary__ilike="1%")
    secured = BasicScope.apply(f, make_ctx(["hr"]))
    # ilike not in allowed_ops=[eq, gt]
    assert not secured.has_filter_for("salary")


def test_apply_does_not_mutate_original():
    f = EmpFilter(salary__eq=1000.0)
    _ = BasicScope.apply(f, make_ctx(["user"]))
    assert f.has_filter_for("salary")


def test_apply_preserves_order_by():
    f = EmpFilter(order_by="age")
    secured = BasicScope.apply(f, make_ctx())
    assert secured.order_by is not None
    assert secured.order_by.field == "age"


def test_apply_bypass_returns_original_reference():
    class AdminScope(ScopeBase):
        bypass_if = staticmethod(lambda ctx: "admin" in ctx.user.roles)
        filter_scopes = {"salary": FilterScope(rule=AccessRule(allow_if=lambda ctx: False))}

    f = EmpFilter(salary__eq=999.0)
    secured = AdminScope.apply(f, make_ctx(["admin"]))
    assert secured is f


def test_apply_strict_drops_unregistered_fields():
    class Strict(ScopeBase, strict=True):
        filter_scopes = {"name": FilterScope()}

    f = EmpFilter(name__eq="Alice", age__gt=18)
    secured = Strict.apply(f, make_ctx())
    assert secured.has_filter_for("name")
    assert not secured.has_filter_for("age")


def test_apply_registers_row_rule():
    class OrgScope(ScopeBase):
        row_rule = RowRule(condition=lambda ctx, m: m.department == ctx.user.organization_id)

    f = EmpFilter(name__eq="Alice")
    secured = OrgScope.apply(f, make_ctx(org_id=7))
    assert len(secured._scope_row_rules) == 1


def test_apply_stacks_row_rules():
    class ScopeA(ScopeBase):
        row_rule = RowRule(condition=lambda ctx, m: m.department == "A")

    class ScopeB(ScopeBase):
        row_rule = RowRule(condition=lambda ctx, m: m.age > 18)

    f = EmpFilter(name__eq="test")
    f_a = ScopeA.apply(f, make_ctx())
    f_ab = ScopeB.apply(f_a, make_ctx())
    assert len(f_ab._scope_row_rules) == 2


# ---------------------------------------------------------------------------
# apply_selection integration with scope row rules
# ---------------------------------------------------------------------------

class ScopeTestBase(DeclarativeBase):
    pass


class Emp(ScopeTestBase):
    __tablename__ = "scope_employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    org_id: Mapped[int] = mapped_column(Integer)


@pytest_asyncio.fixture
async def scope_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(ScopeTestBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def scope_session(scope_engine):
    maker = async_sessionmaker(scope_engine, expire_on_commit=False)
    async with maker() as session:
        session.add_all([
            Emp(id=1, name="Alice",   age=30, org_id=1),
            Emp(id=2, name="Bob",     age=25, org_id=1),
            Emp(id=3, name="Charlie", age=35, org_id=2),
        ])
        await session.commit()
        yield session


class OrgEmpFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]


class OrgScope(ScopeBase):
    row_rule = RowRule(condition=lambda ctx, m: m.org_id == ctx.user.organization_id)


@pytest.mark.asyncio
async def test_apply_selection_with_row_rule(scope_session):
    ctx = make_ctx(org_id=1)
    f = OrgEmpFilter(name__eq="Alice")
    secured = OrgScope.apply(f, ctx)

    q = apply_selection(select(Emp), Emp, secured)
    result = (await scope_session.execute(q)).scalars().all()
    assert len(result) == 1
    assert result[0].name == "Alice"


@pytest.mark.asyncio
async def test_row_rule_filters_by_org(scope_session):
    ctx = make_ctx(org_id=1)
    f = OrgEmpFilter()
    secured = OrgScope.apply(f, ctx)

    q = apply_selection(select(Emp), Emp, secured)
    result = (await scope_session.execute(q)).scalars().all()
    assert all(e.org_id == 1 for e in result)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_row_rule_other_org(scope_session):
    ctx = make_ctx(org_id=2)
    f = OrgEmpFilter()
    secured = OrgScope.apply(f, ctx)

    q = apply_selection(select(Emp), Emp, secured)
    result = (await scope_session.execute(q)).scalars().all()
    assert len(result) == 1
    assert result[0].name == "Charlie"


# ---------------------------------------------------------------------------
# Public API importable from top-level
# ---------------------------------------------------------------------------

def test_security_importable_from_top_level():
    from web_fractal import (
        AccessDenied, AccessRule, EnvContext, FieldDecision,
        FieldNotVisible, FieldScope, FilterScope, OperationNotAllowed,
        RowRule, ScopeBase, SecurityContext, UserPrincipal,
    )
    assert ScopeBase is not None
    assert SecurityContext is not None
