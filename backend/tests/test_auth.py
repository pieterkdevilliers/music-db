import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "test@example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "short@example.com", "password": "abc"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "login@example.com", "password": "password123"}
    )
    resp = await client.post(
        "/auth/login", data={"username": "login@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "wp@example.com", "password": "password123"}
    )
    resp = await client.post(
        "/auth/login", data={"username": "wp@example.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "me@example.com", "password": "password123"}
    )
    login = await client.post(
        "/auth/login", data={"username": "me@example.com", "password": "password123"}
    )
    token = login.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
