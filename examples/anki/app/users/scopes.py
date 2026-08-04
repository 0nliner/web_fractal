"""
UserScope — ABAC rules for the user domain.

Demonstrates FieldScope: email is masked for non-admin users.
In a real app you'd add a RowRule if users shouldn't see each other at all.
"""
from web_fractal.core.security import AccessRule, FieldScope, ScopeBase


class UserScope(ScopeBase, strict=False):
    bypass_if = staticmethod(lambda ctx: ctx.user.extra.get("role") == "admin")

    field_scopes = {
        "email": FieldScope(
            visible=AccessRule(allow_if=lambda ctx: ctx.user.extra.get("role") == "admin"),
            mask_with="***@***",
        ),
    }
