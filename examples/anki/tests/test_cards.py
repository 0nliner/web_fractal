"""
Cards — tests covering CRUD, FilterBase DSL, and the SM-2 spaced repetition algorithm.

The review endpoint (POST /cards/{id}/review) is the domain highlight:
it's a non-standard route that required manual init_http_routes() in CardsController.
"""
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

async def _setup(client, *, username="tester"):
    user = (await client.post("/users/", json={"username": username, "email": f"{username}@ex.com"})).json()
    deck = (await client.post("/decks/", json={"owner_id": user["id"], "title": "ML Flashcards"})).json()
    return user, deck


async def _card(client, deck_id, front="Q", back="A"):
    return (await client.post("/cards/", json={"deck_id": deck_id, "front": front, "back": back})).json()


# ── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_card(client):
    _, deck = await _setup(client)
    resp = await client.post("/cards/", json={
        "deck_id": deck["id"],
        "front": "What is gradient descent?",
        "back": "An iterative optimisation algorithm that minimises a loss function.",
    })
    assert resp.status_code == 200
    card = resp.json()
    assert card["front"] == "What is gradient descent?"
    assert card["interval"] == 1
    assert card["repetitions"] == 0
    assert card["ease_factor"] == 2.5
    assert card["due_date"] is None


@pytest.mark.asyncio
async def test_get_card_not_found(client):
    resp = await client.get("/cards/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_cards_by_deck(client):
    """FilterBase DSL: deck_id__eq isolates cards to one deck."""
    _, deck_a = await _setup(client, username="u1")
    _, deck_b = await _setup(client, username="u2")

    await _card(client, deck_a["id"], "A1")
    await _card(client, deck_a["id"], "A2")
    await _card(client, deck_b["id"], "B1")

    resp = await client.get("/cards/", params={"deck_id__eq": deck_a["id"]})
    cards = resp.json()
    assert len(cards) == 2
    assert all(c["deck_id"] == deck_a["id"] for c in cards)


@pytest.mark.asyncio
async def test_update_card(client):
    _, deck = await _setup(client, username="u3")
    card = await _card(client, deck["id"], "Old front")

    resp = await client.patch(f"/cards/{card['id']}", json={"front": "New front"})
    assert resp.status_code == 200
    assert resp.json()["front"] == "New front"
    assert resp.json()["back"] == "A"  # unchanged


@pytest.mark.asyncio
async def test_delete_card(client):
    _, deck = await _setup(client, username="u4")
    card = await _card(client, deck["id"])
    await client.delete(f"/cards/{card['id']}")
    assert (await client.get(f"/cards/{card['id']}")).status_code == 404


# ── SM-2 spaced repetition ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_perfect_recall(client):
    """grade=5: first review sets interval=1, repetitions=1, ease increases."""
    _, deck = await _setup(client, username="r1")
    card = await _card(client, deck["id"])

    resp = await client.post(f"/cards/{card['id']}/review", json={"grade": 5})
    assert resp.status_code == 200
    reviewed = resp.json()
    assert reviewed["repetitions"] == 1
    assert reviewed["interval"] == 1          # first successful review → 1 day
    assert reviewed["ease_factor"] > 2.5      # grade=5 increases ease
    assert reviewed["due_date"] is not None


@pytest.mark.asyncio
async def test_review_second_recall(client):
    """Second successful review → interval=6."""
    _, deck = await _setup(client, username="r2")
    card = await _card(client, deck["id"])

    await client.post(f"/cards/{card['id']}/review", json={"grade": 5})
    resp = await client.post(f"/cards/{card['id']}/review", json={"grade": 5})
    reviewed = resp.json()
    assert reviewed["repetitions"] == 2
    assert reviewed["interval"] == 6


@pytest.mark.asyncio
async def test_review_blackout_resets(client):
    """grade=0 (blackout) resets repetitions and interval to 1."""
    _, deck = await _setup(client, username="r3")
    card = await _card(client, deck["id"])

    # Two successful reviews first
    await client.post(f"/cards/{card['id']}/review", json={"grade": 5})
    await client.post(f"/cards/{card['id']}/review", json={"grade": 5})

    # Blackout
    resp = await client.post(f"/cards/{card['id']}/review", json={"grade": 0})
    reset = resp.json()
    assert reset["repetitions"] == 0
    assert reset["interval"] == 1
    assert reset["ease_factor"] < 2.5  # ease degrades on failure


@pytest.mark.asyncio
async def test_review_grade_validation(client):
    """grade must be 0–5; anything else is rejected by Pydantic."""
    _, deck = await _setup(client, username="r4")
    card = await _card(client, deck["id"])

    resp = await client.post(f"/cards/{card['id']}/review", json={"grade": 6})
    assert resp.status_code == 422

    resp = await client.post(f"/cards/{card['id']}/review", json={"grade": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_card_not_found(client):
    resp = await client.post("/cards/9999/review", json={"grade": 3})
    assert resp.status_code == 404
