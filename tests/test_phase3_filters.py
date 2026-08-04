"""
Phase 3 tests: Expression DSL — FilterBase, FilterField, Op, OrderBy, apply_selection
"""
import datetime
import uuid
from enum import Enum
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from web_fractal.filters import (
    FilterBase,
    FilterField,
    Op,
    OrderBy,
    ParsedExpression,
    TYPES_AVAILABLE_OPS,
    apply_selection,
)


# ---------------------------------------------------------------------------
# Test models / enums / filters
# ---------------------------------------------------------------------------

class Role(Enum):
    admin = "admin"
    user = "user"
    moderator = "moderator"


class EmployeeFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]
    role: FilterField[Role]
    salary: FilterField[float]


class UUIDFilter(FilterBase):
    uid: FilterField[uuid.UUID]


# ---------------------------------------------------------------------------
# Op enum
# ---------------------------------------------------------------------------

def test_op_enum_values():
    assert Op.eq.value == "eq"
    assert Op.is_null.value == "is_null"
    assert Op.in_.value == "in_"


# ---------------------------------------------------------------------------
# TYPES_AVAILABLE_OPS
# ---------------------------------------------------------------------------

def test_str_ops():
    assert Op.ilike in TYPES_AVAILABLE_OPS[str]
    assert Op.gt not in TYPES_AVAILABLE_OPS[str]


def test_int_ops():
    assert Op.gt in TYPES_AVAILABLE_OPS[int]
    assert Op.ilike not in TYPES_AVAILABLE_OPS[int]


def test_bool_ops():
    ops = TYPES_AVAILABLE_OPS[bool]
    assert Op.eq in ops
    assert Op.gt not in ops
    assert Op.ilike not in ops


def test_uuid_ops():
    assert uuid.UUID in TYPES_AVAILABLE_OPS
    ops = TYPES_AVAILABLE_OPS[uuid.UUID]
    assert Op.eq in ops
    assert Op.in_ in ops
    assert Op.is_null in ops
    assert Op.gt not in ops
    assert Op.ilike not in ops


# ---------------------------------------------------------------------------
# FilterBase parsing
# ---------------------------------------------------------------------------

def test_simple_eq():
    f = EmployeeFilter(name__eq="Alice")
    exprs = f.active_expressions
    assert len(exprs) == 1
    assert exprs[0] == ParsedExpression("name", Op.eq, "Alice")


def test_multiple_expressions():
    f = EmployeeFilter(name__ilike="%ali%", age__gt=18)
    exprs = f.active_expressions
    assert len(exprs) == 2
    fields = {e.field_name for e in exprs}
    assert fields == {"name", "age"}


def test_none_values_ignored():
    f = EmployeeFilter(name__eq=None, age__gt=18)
    assert len(f.active_expressions) == 1
    assert f.active_expressions[0].field_name == "age"


def test_unknown_field_ignored():
    f = EmployeeFilter(nonexistent__eq="foo")
    assert f.active_expressions == []


def test_invalid_op_string_ignored():
    f = EmployeeFilter(name__turbofilter="foo")
    assert f.active_expressions == []


def test_op_invalid_for_type_ignored():
    # gt is not valid for str type
    f = EmployeeFilter(name__gt="foo")
    assert f.active_expressions == []


def test_op_invalid_for_type_int_ilike_ignored():
    # ilike is not valid for int type
    f = EmployeeFilter(age__ilike="foo")
    assert f.active_expressions == []


def test_field_no_op_defaults_to_eq():
    f = EmployeeFilter(age=42)
    exprs = f.active_expressions
    assert len(exprs) == 1
    assert exprs[0].op == Op.eq
    assert exprs[0].value == 42


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------

def test_int_coercion():
    f = EmployeeFilter(age__eq="25")
    assert f.active_expressions[0].value == 25
    assert isinstance(f.active_expressions[0].value, int)


def test_float_coercion():
    f = EmployeeFilter(salary__gt="1500.50")
    assert f.active_expressions[0].value == 1500.5


def test_in_coercion_comma_string():
    f = EmployeeFilter(age__in_="18,25,30")
    assert f.active_expressions[0].value == [18, 25, 30]


def test_in_coercion_list():
    f = EmployeeFilter(age__in_=[18, 25, 30])
    assert f.active_expressions[0].value == [18, 25, 30]


def test_is_null_bool_true():
    f = EmployeeFilter(name__is_null=True)
    assert f.active_expressions[0].value is True


def test_is_null_string_true():
    f = EmployeeFilter(name__is_null="true")
    assert f.active_expressions[0].value is True


def test_is_null_string_false():
    f = EmployeeFilter(name__is_null="false")
    assert f.active_expressions[0].value is False


def test_is_null_string_1():
    f = EmployeeFilter(name__is_null="1")
    assert f.active_expressions[0].value is True


# ---------------------------------------------------------------------------
# Enum coercion — eq, neq, in_  (must try value AND name)
# ---------------------------------------------------------------------------

def test_enum_coerce_by_value():
    f = EmployeeFilter(role__eq="admin")
    assert f.active_expressions[0].value == Role.admin


def test_enum_coerce_by_name():
    # same as value in this enum, but let's test the name path
    f = EmployeeFilter(role__eq="moderator")
    assert f.active_expressions[0].value == Role.moderator


def test_enum_coerce_instance_passthrough():
    f = EmployeeFilter(role__eq=Role.user)
    assert f.active_expressions[0].value == Role.user


def test_enum_in_coerce_by_value():
    """in_ with Enum must try value/name per item — was a bug (only tried value)."""
    f = EmployeeFilter(role__in_="admin,user")
    result = f.active_expressions[0].value
    assert result == [Role.admin, Role.user]


def test_enum_in_coerce_by_name():
    """Each item in in_ list: falls back to name lookup when value lookup fails."""
    class Status(Enum):
        active = 1
        inactive = 2

    class StatusFilter(FilterBase):
        status: FilterField[Status]

    f = StatusFilter(status__in_="active,inactive")
    result = f.active_expressions[0].value
    assert result == [Status.active, Status.inactive]


def test_enum_in_coerce_mixed_instance_string():
    f = EmployeeFilter(role__in_=[Role.admin, "user"])
    result = f.active_expressions[0].value
    assert result == [Role.admin, Role.user]


# ---------------------------------------------------------------------------
# UUID coercion
# ---------------------------------------------------------------------------

def test_uuid_coerce_from_string():
    uid = uuid.uuid4()
    f = UUIDFilter(uid__eq=str(uid))
    assert f.active_expressions[0].value == uid


def test_uuid_in_coerce():
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    f = UUIDFilter(uid__in_=f"{u1},{u2}")
    assert f.active_expressions[0].value == [u1, u2]


def test_uuid_coerce_from_uuid_instance():
    """Значение уже нужного типа не приводится повторно.

    Именно этот путь и работает в бою: as_fastapi_dep() объявляет query-параметр
    с аннотацией uuid.UUID, поэтому FastAPI приводит строку сам, и в _coerce
    приезжает готовый UUID. UUID(UUID(...)) кидает AttributeError — раньше его
    не было в перехвате, и запрос отвечал 500-й.
    """
    uid = uuid.uuid4()
    f = UUIDFilter(uid__eq=uid)
    assert f.active_expressions[0].value == uid


def test_uuid_in_coerce_from_uuid_instances():
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    f = UUIDFilter(uid__in_=[u1, u2])
    assert f.active_expressions[0].value == [u1, u2]


# ---------------------------------------------------------------------------
# OrderBy
# ---------------------------------------------------------------------------

def test_order_by_asc():
    ob = OrderBy("name")
    assert ob.field == "name"
    assert ob.ascending is True
    assert ob.is_set is True


def test_order_by_desc():
    ob = OrderBy("-name")
    assert ob.field == "name"
    assert ob.ascending is False


def test_order_by_none():
    ob = OrderBy(None)
    assert ob.is_set is False


def test_order_by_empty_string():
    ob = OrderBy("")
    assert ob.is_set is False


def test_filter_order_by_string():
    f = EmployeeFilter(order_by="age")
    assert f.order_by is not None
    assert f.order_by.field == "age"
    assert f.order_by.ascending is True


def test_filter_order_by_desc():
    f = EmployeeFilter(order_by="-age")
    assert f.order_by.field == "age"
    assert f.order_by.ascending is False


def test_filter_order_by_instance():
    ob = OrderBy("-name")
    f = EmployeeFilter(order_by=ob)
    assert f.order_by is ob


# ---------------------------------------------------------------------------
# FilterBase helpers
# ---------------------------------------------------------------------------

def test_has_filter_for_true():
    f = EmployeeFilter(name__eq="Alice")
    assert f.has_filter_for("name") is True


def test_has_filter_for_false():
    f = EmployeeFilter(age__gt=18)
    assert f.has_filter_for("name") is False


def test_active_expressions_returns_copy():
    f = EmployeeFilter(name__eq="Alice")
    exprs1 = f.active_expressions
    exprs2 = f.active_expressions
    assert exprs1 is not exprs2
    assert exprs1 == exprs2


def test_repr():
    f = EmployeeFilter(name__eq="Alice")
    r = repr(f)
    assert "EmployeeFilter" in r


# ---------------------------------------------------------------------------
# apply_selection — SQLAlchemy integration
# ---------------------------------------------------------------------------

class FilterTestBase(DeclarativeBase):
    pass


class Employee(FilterTestBase):
    __tablename__ = "employees_filter_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)


@pytest_asyncio.fixture
async def employee_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(FilterTestBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def employee_session(employee_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    maker = async_sessionmaker(employee_engine, expire_on_commit=False)
    async with maker() as session:
        session.add_all([
            Employee(id=1, name="Alice", age=30),
            Employee(id=2, name="Bob", age=25),
            Employee(id=3, name="Charlie", age=35),
            Employee(id=4, name="alice_lower", age=20),
        ])
        await session.commit()
        yield session


class EFilter(FilterBase):
    name: FilterField[str]
    age: FilterField[int]


@pytest.mark.asyncio
async def test_apply_selection_eq(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(name__eq="Alice"))
    result = (await employee_session.execute(q)).scalars().all()
    assert len(result) == 1
    assert result[0].name == "Alice"


@pytest.mark.asyncio
async def test_apply_selection_gt(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(age__gt=28))
    result = (await employee_session.execute(q)).scalars().all()
    assert all(e.age > 28 for e in result)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_apply_selection_ilike(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(name__ilike="alice%"))
    result = (await employee_session.execute(q)).scalars().all()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_apply_selection_in(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(age__in_="25,30"))
    result = (await employee_session.execute(q)).scalars().all()
    assert {e.age for e in result} == {25, 30}


@pytest.mark.asyncio
async def test_apply_selection_multiple_conditions(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(age__gte=25, age__lte=30))
    result = (await employee_session.execute(q)).scalars().all()
    assert all(25 <= e.age <= 30 for e in result)


@pytest.mark.asyncio
async def test_apply_selection_order_by_asc(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(order_by="age"))
    result = (await employee_session.execute(q)).scalars().all()
    ages = [e.age for e in result]
    assert ages == sorted(ages)


@pytest.mark.asyncio
async def test_apply_selection_order_by_desc(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter(order_by="-age"))
    result = (await employee_session.execute(q)).scalars().all()
    ages = [e.age for e in result]
    assert ages == sorted(ages, reverse=True)


@pytest.mark.asyncio
async def test_apply_selection_no_filters_returns_all(employee_session):
    q = apply_selection(select(Employee), Employee, EFilter())
    result = (await employee_session.execute(q)).scalars().all()
    assert len(result) == 4


@pytest.mark.asyncio
async def test_apply_selection_unknown_column_skipped(employee_session):
    class BrokenFilter(FilterBase):
        nonexistent: FilterField[str]

    f = BrokenFilter.__new__(BrokenFilter)
    f._expressions = [ParsedExpression("nonexistent", Op.eq, "val")]
    f.order_by = None
    q = apply_selection(select(Employee), Employee, f)
    result = (await employee_session.execute(q)).scalars().all()
    assert len(result) == 4


# ---------------------------------------------------------------------------
# as_fastapi_dep (signature inspection — no FastAPI server needed)
# ---------------------------------------------------------------------------

def test_as_fastapi_dep_signature():
    import inspect
    dep = EmployeeFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    param_names = set(sig.parameters.keys())

    assert "name__eq" in param_names
    assert "name__ilike" in param_names
    assert "name__like" in param_names
    assert "name__in_" in param_names
    assert "age__gt" in param_names
    assert "age__gte" in param_names
    assert "age__lt" in param_names
    assert "age__lte" in param_names
    assert "order_by" in param_names


def test_as_fastapi_dep_no_invalid_ops_for_str():
    """gt/lt/gte/lte must NOT appear for str fields."""
    import inspect
    dep = EmployeeFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    param_names = set(sig.parameters.keys())
    assert "name__gt" not in param_names
    assert "name__lt" not in param_names


def test_as_fastapi_dep_in_annotation_is_optional_str():
    """in_ params must be Optional[str] (comma-separated)."""
    import inspect
    dep = EmployeeFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    p = sig.parameters["name__in_"]
    import typing
    args = typing.get_args(p.annotation)
    assert str in args


def test_as_fastapi_dep_is_null_annotation_is_optional_bool():
    import inspect
    dep = EmployeeFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    p = sig.parameters["name__is_null"]
    import typing
    args = typing.get_args(p.annotation)
    assert bool in args


def test_as_fastapi_dep_returns_filter_instance():
    dep = EmployeeFilter.as_fastapi_dep()
    result = dep(name__eq="Alice", age__gt=18)
    assert isinstance(result, EmployeeFilter)
    assert result.has_filter_for("name")
    assert result.has_filter_for("age")


def test_as_fastapi_dep_name():
    dep = EmployeeFilter.as_fastapi_dep()
    assert "EmployeeFilter" in dep.__name__


def test_as_fastapi_dep_enum_ops():
    """Enum fields should expose eq, neq, in_, is_null — but not gt/ilike."""
    import inspect
    dep = EmployeeFilter.as_fastapi_dep()
    sig = inspect.signature(dep)
    param_names = set(sig.parameters.keys())
    assert "role__eq" in param_names
    assert "role__in_" in param_names
    assert "role__is_null" in param_names
    assert "role__gt" not in param_names
    assert "role__ilike" not in param_names
