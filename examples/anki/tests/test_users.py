"""
Users — HTTP CRUD tests.

Demonstrates:
- GenericRepo/Service giving full CRUD with ~5 lines of code
- FilterBase DSL query params (?username__ilike=ali)
- UnitOfWork transaction per request (auto-committed by the controller)
"""
import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    resp = await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["role"] == "student"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_user(client):
    created = (await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})).json()
    resp = await client.get(f"/users/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_get_user_not_found(client):
    resp = await client.get("/users/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_username_ilike(client):
    """FilterBase DSL: username__ilike=ali matches 'alice' but not 'bob'."""
    await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})
    await client.post("/users/", json={"username": "bob",   "email": "bob@example.com"})

    resp = await client.get("/users/", params={"username__ilike": "%ali%"})
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["username"] == "alice"


@pytest.mark.asyncio
async def test_filter_by_role(client):
    """FilterBase DSL: role__eq filters exactly."""
    await client.post("/users/", json={"username": "alice", "email": "alice@example.com", "role": "student"})
    await client.post("/users/", json={"username": "admin", "email": "admin@example.com", "role": "admin"})

    resp = await client.get("/users/", params={"role__eq": "admin"})
    users = resp.json()
    assert len(users) == 1
    assert users[0]["username"] == "admin"


@pytest.mark.asyncio
async def test_update_user(client):
    user = (await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})).json()

    resp = await client.patch(f"/users/{user['id']}", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_update_empty_body_422(client):
    user = (await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})).json()
    resp = await client.patch(f"/users/{user['id']}", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_user(client):
    user = (await client.post("/users/", json={"username": "alice", "email": "alice@example.com"})).json()

    await client.delete(f"/users/{user['id']}")

    resp = await client.get(f"/users/{user['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client):
    resp = await client.delete("/users/9999")
    assert resp.status_code == 404
