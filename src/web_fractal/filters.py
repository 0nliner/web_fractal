"""
Expression DSL for type-safe query filtering.

Usage:
    class UserFilter(FilterBase):
        name: FilterField[str]
        age:  FilterField[int]
        role: FilterField[MyRoleEnum]

    # FastAPI dependency — generates explicit Query params in Swagger:
    UserFilterDep = UserFilter.as_fastapi_dep()

    @router.get("/users")
    async def list_users(filter: Annotated[UserFilter, Depends(UserFilterDep)]):
        query = apply_selection(select(User), User, filter)
        ...

    # Apply filters to a SQLAlchemy query:
    query = apply_selection(select(User), User, user_filter)

    # Backward-compat helper (dict-based) is still available in db.py as apply_filters().
"""

import datetime
import inspect
import uuid
from enum import Enum
from typing import Any, Callable, Generic, Optional, Type, TypeVar, get_args, get_origin, get_type_hints

T = TypeVar("T")
Q = TypeVar("Q")


# ---------------------------------------------------------------------------
# Op enum
# ---------------------------------------------------------------------------

class Op(Enum):
    eq      = "eq"
    neq     = "neq"
    gt      = "gt"
    lt      = "lt"
    gte     = "gte"
    lte     = "lte"
    ilike   = "ilike"
    like    = "like"
    in_     = "in_"
    is_null = "is_null"


_OP_TO_SA_METHOD: dict[Op, str] = {
    Op.eq:      "__eq__",
    Op.neq:     "__ne__",
    Op.gt:      "__gt__",
    Op.lt:      "__lt__",
    Op.gte:     "__ge__",
    Op.lte:     "__le__",
    Op.ilike:   "ilike",
    Op.like:    "like",
    Op.in_:     "in_",
    Op.is_null: "is_",
}


# ---------------------------------------------------------------------------
# Type → available ops mapping
# ---------------------------------------------------------------------------

TYPES_AVAILABLE_OPS: dict[type, list[Op]] = {
    str: [Op.eq, Op.neq, Op.ilike, Op.like, Op.in_, Op.is_null],
    int: [Op.eq, Op.neq, Op.gt, Op.lt, Op.gte, Op.lte, Op.in_, Op.is_null],
    float: [Op.eq, Op.neq, Op.gt, Op.lt, Op.gte, Op.lte, Op.in_, Op.is_null],
    bool: [Op.eq, Op.neq, Op.is_null],
    datetime.datetime: [Op.eq, Op.neq, Op.gt, Op.lt, Op.gte, Op.lte, Op.is_null],
    datetime.date: [Op.eq, Op.neq, Op.gt, Op.lt, Op.gte, Op.lte, Op.is_null],
    uuid.UUID: [Op.eq, Op.neq, Op.in_, Op.is_null],
}


def _get_ops_for_type(field_type: type) -> list[Op]:
    if field_type in TYPES_AVAILABLE_OPS:
        return TYPES_AVAILABLE_OPS[field_type]
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        return [Op.eq, Op.neq, Op.in_, Op.is_null]
    return [Op.eq, Op.neq, Op.is_null]


# ---------------------------------------------------------------------------
# FilterField marker type
# ---------------------------------------------------------------------------

class FilterField(Generic[T]):
    """
    Type marker for FilterBase field declarations.

    class UserFilter(FilterBase):
        name: FilterField[str]
        age:  FilterField[int]
    """
    pass


def _is_filter_field(annotation: Any) -> bool:
    return get_origin(annotation) is FilterField


def _unwrap_filter_field_type(annotation: Any) -> type:
    args = get_args(annotation)
    return args[0] if args else Any


# ---------------------------------------------------------------------------
# OrderBy
# ---------------------------------------------------------------------------

class OrderBy:
    """
    Ordering specification parsed from a query param.

    'name'   → ASC  by 'name'
    '-name'  → DESC by 'name'
    """

    def __init__(self, field: Optional[str] = None):
        if field and field.startswith('-'):
            self.field: Optional[str] = field[1:]
            self.ascending = False
        else:
            self.field = field or None
            self.ascending = True

    @property
    def is_set(self) -> bool:
        return self.field is not None

    def __repr__(self) -> str:
        direction = "ASC" if self.ascending else "DESC"
        return f"OrderBy({self.field!r}, {direction})"


# ---------------------------------------------------------------------------
# ParsedExpression — internal value object
# ---------------------------------------------------------------------------

class ParsedExpression:
    __slots__ = ("field_name", "op", "value")

    def __init__(self, field_name: str, op: Op, value: Any) -> None:
        self.field_name = field_name
        self.op = op
        self.value = value

    def __repr__(self) -> str:
        return f"ParsedExpression({self.field_name!r}, {self.op!r}, {self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParsedExpression):
            return NotImplemented
        return (self.field_name, self.op, self.value) == (other.field_name, other.op, other.value)


# ---------------------------------------------------------------------------
# FilterBase
# ---------------------------------------------------------------------------

class FilterBase:
    """
    Base class for filter specifications.

    Declare fields with FilterField[T]. Instantiate by passing field__op=value
    keyword arguments (typically via as_fastapi_dep()).
    """

    def __init__(self, **kwargs: Any) -> None:
        self._expressions: list[ParsedExpression] = []
        self.order_by: Optional[OrderBy] = None
        self._scope_row_rules: list = []  # populated by ScopeBase.apply()

        filter_fields = self.__class__._get_filter_fields()

        for key, value in kwargs.items():
            if value is None:
                continue

            if key == "order_by":
                self.order_by = OrderBy(value) if isinstance(value, str) else value
                continue

            if "__" in key:
                field_name, op_str = key.rsplit("__", 1)
            else:
                field_name, op_str = key, "eq"

            if field_name not in filter_fields:
                continue

            try:
                op = Op(op_str)
            except ValueError:
                continue

            field_type = filter_fields[field_name]
            if op not in _get_ops_for_type(field_type):
                continue
            coerced = self._coerce(value, field_type, op)
            self._expressions.append(ParsedExpression(field_name, op, coerced))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_enum(enum_type: type, value: Any) -> Any:
        if isinstance(value, enum_type):
            return value
        try:
            return enum_type(value)
        except ValueError:
            try:
                return enum_type[value]
            except KeyError:
                return value

    def _coerce(self, value: Any, field_type: type, op: Op) -> Any:
        if op == Op.in_:
            items = [v.strip() for v in value.split(",")] if isinstance(value, str) else list(value)
            if isinstance(field_type, type) and issubclass(field_type, Enum):
                return [self._coerce_enum(field_type, item) for item in items]
            try:
                return [
                    item if isinstance(item, field_type) else field_type(item)
                    for item in items
                ]
            except (ValueError, TypeError, AttributeError):
                return items

        if op == Op.is_null:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return self._coerce_enum(field_type, value)

        # Значение может УЖЕ быть нужного типа: as_fastapi_dep() объявляет
        # query-параметр с аннотацией из FilterField[T], поэтому FastAPI приводит
        # строку к T раньше, чем она попадёт сюда. Повторное приведение UUID(UUID(...))
        # кидает AttributeError, которого не было в списке перехвата, — и любой
        # фильтр по UUID отвечал 500-й.
        if isinstance(field_type, type) and isinstance(value, field_type):
            return value

        try:
            return field_type(value)
        except (ValueError, TypeError, AttributeError):
            return value

    # ------------------------------------------------------------------
    # Class-level introspection
    # ------------------------------------------------------------------

    @classmethod
    def _get_filter_fields(cls) -> dict[str, type]:
        """Returns {field_name: inner_type} for all FilterField[T] annotations."""
        try:
            hints = get_type_hints(cls)
        except Exception:
            hints = getattr(cls, "__annotations__", {})

        result = {}
        for name, annotation in hints.items():
            if name.startswith("_"):
                continue
            if _is_filter_field(annotation):
                result[name] = _unwrap_filter_field_type(annotation)
        return result

    # ------------------------------------------------------------------
    # FastAPI integration
    # ------------------------------------------------------------------

    @classmethod
    def as_fastapi_dep(cls) -> Callable:
        """
        Returns a FastAPI-compatible dependency function.

        FastAPI reads __signature__ to register explicit Query params
        in Swagger. The actual function collects **kwargs and builds
        a FilterBase instance from them.
        """
        from fastapi import Query

        filter_fields = cls._get_filter_fields()
        parameters: list[inspect.Parameter] = []

        for field_name, field_type in filter_fields.items():
            for op in _get_ops_for_type(field_type):
                param_name = f"{field_name}__{op.value}"
                if op == Op.in_:
                    annotation = Optional[str]
                elif op == Op.is_null:
                    annotation = Optional[bool]
                else:
                    annotation = Optional[field_type]

                parameters.append(inspect.Parameter(
                    name=param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(default=None),
                    annotation=annotation,
                ))

        parameters.append(inspect.Parameter(
            name="order_by",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=Query(default=None),
            annotation=Optional[str],
        ))

        _cls = cls

        def _dep(**kwargs: Any) -> _cls:
            return _cls(**{k: v for k, v in kwargs.items() if v is not None})

        _dep.__signature__ = inspect.Signature(parameters, return_annotation=cls)
        _dep.__name__ = f"{cls.__name__}_dep"
        _dep.__qualname__ = f"{cls.__qualname__}.dep"
        return _dep

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def active_expressions(self) -> list[ParsedExpression]:
        return list(self._expressions)

    def has_filter_for(self, field_name: str) -> bool:
        return any(e.field_name == field_name for e in self._expressions)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(expressions={self._expressions!r}, order_by={self.order_by!r})"


# ---------------------------------------------------------------------------
# apply_selection
# ---------------------------------------------------------------------------

def _build_where_conditions(model: Type, filter_obj: FilterBase) -> list:
    """Extract reusable WHERE conditions list (used by apply_selection and GenericRepo.update)."""
    conditions = []
    for expr in filter_obj.active_expressions:
        column = getattr(model, expr.field_name, None)
        if column is None:
            continue
        if expr.op == Op.in_:
            conditions.append(column.in_(expr.value))
        elif expr.op == Op.is_null:
            conditions.append(column.is_(None) if expr.value else column.isnot(None))
        else:
            sa_method = _OP_TO_SA_METHOD[expr.op]
            conditions.append(getattr(column, sa_method)(expr.value))
    for rule_fn in getattr(filter_obj, "_scope_row_rules", []):
        conditions.append(rule_fn(model))
    return conditions


def apply_selection(query: Q, model: Type, filter_obj: FilterBase) -> Q:
    """
    Apply FilterBase expressions to a SQLAlchemy query as WHERE conditions.

    Preserves backward-compat: apply_filters(query, model, dict) still works
    for simple dict-based filtering (see db.py).
    """
    conditions = _build_where_conditions(model, filter_obj)

    if conditions:
        query = query.where(*conditions)

    if filter_obj.order_by and filter_obj.order_by.is_set:
        from sqlalchemy import asc, desc
        column = getattr(model, filter_obj.order_by.field, None)
        if column is not None:
            query = query.order_by(
                asc(column) if filter_obj.order_by.ascending else desc(column)
            )

    return query


# ---------------------------------------------------------------------------
# auto_join (stub — nested filter support is in roadmap)
# ---------------------------------------------------------------------------

def auto_join(query: Q, filter_obj: FilterBase) -> Q:
    """
    Add JOINs for nested FilterBase fields.

    Currently a pass-through. Nested filter support requires
    FilterField[AnotherFilter] annotation and relationship inspection.
    """
    return query
