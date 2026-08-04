"""
Decks — tests covering CRUD and ABAC scope.

Key test: test_scope_row_rule verifies that DeckScope.apply() adds a
row-level WHERE clause that restricts results to (owner_id = me) OR (is_public = True).
This is tested directly against the domain objects — no HTTP needed for scope logic.
"""
import pytest

from web_fractal.core.security import SecurityContext, UserPrincipal
from web_fractal.filters import FilterBase

from app.decks.filters import DeckFilter
from app.decks.scopes import DeckScope


# ── helpers ──────────────────────────────────────────────────────────────────

async def _user(client, username, email=None):
    return (await client.post("/users/", json={"username": username, "email": email or f"{username}@ex.com"})).json()


async def _deck(client, owner_id, title, is_public=False):
    return (await client.post("/decks/", json={"owner_id": owner_id, "title": title, "is_public": is_public})).json()


# ── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_deck(client):
    user = await _user(client, "alice")
    resp = await client.post("/decks/", json={"owner_id": user["id"], "title": "Python Basics"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Python Basics"
    assert resp.json()["is_public"] is False


@pytest.mark.asyncio
async def test_get_deck_not_found(client):
    resp = await client.get("/decks/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_decks_by_owner(client):
    alice = await _user(client, "alice")
    bob   = await _user(client, "bob", "bob@ex.com")
    await _deck(client, alice["id"], "Alice Deck")
    await _deck(client, bob["id"],   "Bob Deck")

    resp = await client.get("/decks/", params={"owner_id__eq": alice["id"]})
    decks = resp.json()
    assert len(decks) == 1
    assert decks[0]["title"] == "Alice Deck"


@pytest.mark.asyncio
async def test_update_deck(client):
    user = await _user(client, "alice")
    deck = await _deck(client, user["id"], "Draft")

    resp = await client.patch(f"/decks/{deck['id']}", json={"title": "Final", "is_public": True})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "Final"
    assert updated["is_public"] is True


@pytest.mark.asyncio
async def test_delete_deck(client):
    user = await _user(client, "alice")
    deck = await _deck(client, user["id"], "Temp")
    await client.delete(f"/decks/{deck['id']}")
    assert (await client.get(f"/decks/{deck['id']}")).status_code == 404


# ── ABAC scope tests (domain-level, no HTTP) ─────────────────────────────────

def _ctx(user_id: int, role: str = "student") -> SecurityContext:
    return SecurityContext(user=UserPrincipal(id=user_id, extra={"role": role}))


def test_scope_row_rule_added_for_regular_user():
    """DeckScope.apply() injects a row rule for non-admin users."""
    selection = DeckFilter()
    secured = DeckScope.apply(selection, _ctx(user_id=1))
    assert len(secured._scope_row_rules) == 1


def test_scope_admin_bypass():
    """Admin users skip all scope rules — no row rule injected."""
    selection = DeckFilter()
    secured = DeckScope.apply(selection, _ctx(user_id=99, role="admin"))
    assert len(secured._scope_row_rules) == 0


def test_scope_owner_id_filter_blocked_for_student():
    """
    Non-admins can't filter by owner_id — DeckScope strips that expression.
    This prevents enumerating other users' decks via owner_id__eq=<target>.
    """
    selection = DeckFilter(owner_id__eq=42)
    secured = DeckScope.apply(selection, _ctx(user_id=1, role="student"))
    assert not secured.has_filter_for("owner_id")


def test_scope_owner_id_filter_allowed_for_admin():
    selection = DeckFilter(owner_id__eq=42)
    secured = DeckScope.apply(selection, _ctx(user_id=99, role="admin"))
    assert secured.has_filter_for("owner_id")


@pytest.mark.asyncio
async def test_scope_via_headers(client):
    """
    End-to-end: X-User-Id header activates DeckScope in filter_decks.
    User sees own decks + public decks, not other users' private decks.
    """
    alice = await _user(client, "alice2")
    bob   = await _user(client, "bob2", "bob2@ex.com")

    await _deck(client, alice["id"], "Alice Private", is_public=False)
    await _deck(client, alice["id"], "Alice Public",  is_public=True)
    await _deck(client, bob["id"],   "Bob Private",   is_public=False)

    # Bob's view: Bob's private + Alice's public
    resp = await client.get("/decks/", headers={"x-user-id": str(bob["id"]), "x-user-role": "student"})
    titles = {d["title"] for d in resp.json()}
    assert "Bob Private"   in titles
    assert "Alice Public"  in titles
    assert "Alice Private" not in titles
