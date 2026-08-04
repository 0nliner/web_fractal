from typing import Any, Callable, ClassVar, Optional

from web_fractal.filters import FilterBase, Op
from web_fractal.core.security.context import SecurityContext
from web_fractal.core.security.rules import AccessRule, FieldScope, FilterScope, RowRule


class FieldDecision:
    __slots__ = ("visible", "mask_with")

    def __init__(self, visible: bool, mask_with: Any = None) -> None:
        self.visible = visible
        self.mask_with = mask_with

    def __repr__(self) -> str:
        return f"FieldDecision(visible={self.visible!r}, mask_with={self.mask_with!r})"


class ScopeBase:
    """
    Base class for per-domain ABAC scope declarations.

    Usage:
        class EmployeeScope(ScopeBase, strict=False):
            bypass_if   = lambda ctx: "admin" in ctx.user.roles
            row_rule    = RowRule(lambda ctx, m: m.org_id == ctx.user.organization_id)
            field_scopes   = {"salary": FieldScope(visible=AccessRule(allow_if=lambda ctx: "hr" in ctx.user.roles))}
            filter_scopes  = {"salary": FilterScope(allowed_ops=[Op.eq])}

        secured = EmployeeScope.apply(employee_filter, security_ctx)
        decision = EmployeeScope.evaluate_field("salary", security_ctx)
    """

    _strict: ClassVar[bool] = False

    bypass_if: ClassVar[Optional[Callable[[SecurityContext], bool]]] = None
    row_rule: ClassVar[Optional[RowRule]] = None
    field_scopes: ClassVar[dict[str, FieldScope]] = {}
    filter_scopes: ClassVar[dict[str, FilterScope]] = {}

    def __init_subclass__(cls, strict: bool = False, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._strict = strict
        # each subclass gets its own dicts — not inherited from parent
        if "field_scopes" not in cls.__dict__:
            cls.field_scopes = {}
        if "filter_scopes" not in cls.__dict__:
            cls.filter_scopes = {}

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    @classmethod
    def apply(cls, filter_obj: FilterBase, ctx: SecurityContext) -> FilterBase:
        """
        Return a new FilterBase with:
          - expressions blocked by filter_scopes removed
          - row_rule registered for apply_selection to append as WHERE
        Original filter_obj is never mutated.
        """
        if cls.bypass_if is not None and cls.bypass_if(ctx):
            return filter_obj

        secured: FilterBase = object.__new__(type(filter_obj))
        secured._expressions = []
        secured.order_by = filter_obj.order_by
        secured._scope_row_rules = list(getattr(filter_obj, "_scope_row_rules", []))

        for expr in filter_obj.active_expressions:
            field_name = expr.field_name

            if cls._strict and field_name not in cls.filter_scopes:
                continue

            filter_scope = cls.filter_scopes.get(field_name)
            if filter_scope is not None:
                if not filter_scope.rule.evaluate(ctx):
                    continue
                if filter_scope.allowed_ops is not None and expr.op not in filter_scope.allowed_ops:
                    continue

            secured._expressions.append(expr)

        if cls.row_rule is not None:
            _rr = cls.row_rule
            _ctx = ctx
            secured._scope_row_rules.append(
                lambda model, rr=_rr, c=_ctx: rr.build(c, model)
            )

        return secured

    @classmethod
    def evaluate_field(cls, field_name: str, ctx: SecurityContext) -> FieldDecision:
        """Pure predicate — no DB, safe to call in unit tests."""
        if cls.bypass_if is not None and cls.bypass_if(ctx):
            return FieldDecision(visible=True)

        field_scope = cls.field_scopes.get(field_name)
        if field_scope is None:
            return FieldDecision(visible=not cls._strict)

        visible = field_scope.visible.evaluate(ctx)
        return FieldDecision(
            visible=visible,
            mask_with=field_scope.mask_with if not visible else None,
        )

    @classmethod
    def evaluate_filter(cls, field_name: str, op: Op, ctx: SecurityContext) -> bool:
        """Pure predicate — no DB, safe to call in unit tests."""
        if cls.bypass_if is not None and cls.bypass_if(ctx):
            return True

        if cls._strict and field_name not in cls.filter_scopes:
            return False

        filter_scope = cls.filter_scopes.get(field_name)
        if filter_scope is None:
            return True

        if not filter_scope.rule.evaluate(ctx):
            return False

        if filter_scope.allowed_ops is not None and op not in filter_scope.allowed_ops:
            return False

        return True
