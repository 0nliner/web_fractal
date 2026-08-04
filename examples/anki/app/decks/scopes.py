"""
DeckScope — ABAC rules for the deck domain.

Row rule: each user sees their own decks + any public deck.
Filter rule: only admins can filter by owner_id (prevents enumerating other users' decks).
"""
from sqlalchemy import or_

from web_fractal.core.security import AccessRule, FilterScope, RowRule, ScopeBase


class DeckScope(ScopeBase, strict=False):
    bypass_if = staticmethod(lambda ctx: ctx.user.extra.get("role") == "admin")

    row_rule = RowRule(
        condition=lambda ctx, m: or_(
            m.owner_id == ctx.user.id,
            m.is_public == True,  # noqa: E712 — SQLAlchemy needs == not `is`
        )
    )

    filter_scopes = {
        "owner_id": FilterScope(
            rule=AccessRule(
                allow_if=lambda ctx: ctx.user.extra.get("role") == "admin"
            ),
        ),
    }
