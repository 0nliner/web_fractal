from typing import TYPE_CHECKING, Any, Callable, Optional

from web_fractal.filters import Op

if TYPE_CHECKING:
    from web_fractal.core.security.context import SecurityContext


class AccessRule:
    """
    Lazy predicate — ctx is passed at evaluation time, not at declaration time.
    Both None → default allow.
    deny_if takes precedence over allow_if.
    """

    def __init__(
        self,
        allow_if: Optional[Callable[["SecurityContext"], bool]] = None,
        deny_if: Optional[Callable[["SecurityContext"], bool]] = None,
    ) -> None:
        self.allow_if = allow_if
        self.deny_if = deny_if

    def evaluate(self, ctx: "SecurityContext") -> bool:
        if self.deny_if is not None and self.deny_if(ctx):
            return False
        if self.allow_if is not None:
            return self.allow_if(ctx)
        return True


class RowRule:
    """
    Builds a SQLAlchemy WHERE condition from SecurityContext + model.
    Evaluated lazily — only when apply_selection is called.
    """

    def __init__(self, condition: Callable[["SecurityContext", Any], Any]) -> None:
        self.condition = condition

    def build(self, ctx: "SecurityContext", model: Any) -> Any:
        return self.condition(ctx, model)


class FieldScope:
    """Visibility rule for a single field in query results."""

    def __init__(
        self,
        visible: Optional[AccessRule] = None,
        mask_with: Any = None,
    ) -> None:
        self.visible = visible if visible is not None else AccessRule()
        self.mask_with = mask_with


class FilterScope:
    """Controls which DSL operations are allowed for a filterable field."""

    def __init__(
        self,
        rule: Optional[AccessRule] = None,
        allowed_ops: Optional[list[Op]] = None,
    ) -> None:
        self.rule = rule if rule is not None else AccessRule()
        self.allowed_ops = allowed_ops  # None = all ops permitted
