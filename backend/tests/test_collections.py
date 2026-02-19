import pytest
from httpx import AsyncClient


async def _auth_header(client: AsyncClient, email: str = "coll@example.com") -> dict:
    await client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    login = await client.post(
        "/auth/login", data={"username": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _create_album(client: AsyncClient, headers: dict) -> int:
    resp = await client.post(
        "/albums",
        json={
            "title": "Kind of Blue",
            "artist": "Miles Davis",
            "tracks": ["So What"],
            "musicians": [{"musician_name": "Miles Davis", "instrument": "trumpet"}],
        },
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_collection(client: AsyncClient):
    headers = await _auth_header(client)
    resp = await client.post(
        "/collections",
        json={"name": "Jazz Favourites", "description": "The best jazz records"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Jazz Favourites"


@pytest.mark.asyncio
async def test_list_collections(client: AsyncClient):
    headers = await _auth_header(client, "list@example.com")
    await client.post("/collections", json={"name": "A"}, headers=headers)
    await client.post("/collections", json={"name": "B"}, headers=headers)

    resp = await client.get("/collections", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_add_and_remove_album(client: AsyncClient):
    headers = await _auth_header(client, "addremove@example.com")
    coll = await client.post(
        "/collections", json={"name": "My Collection"}, headers=headers
    )
    coll_id = coll.json()["id"]
    album_id = await _create_album(client, headers)

    add = await client.post(
        f"/collections/{coll_id}/albums/{album_id}", headers=headers
    )
    assert add.status_code == 204

    detail = await client.get(f"/collections/{coll_id}", headers=headers)
    album_ids = [a["id"] for a in detail.json().get("albums", [])]
    assert album_id in album_ids

    remove = await client.delete(
        f"/collections/{coll_id}/albums/{album_id}", headers=headers
    )
    assert remove.status_code == 204


@pytest.mark.asyncio
async def test_update_collection(client: AsyncClient):
    headers = await _auth_header(client, "upd@example.com")
    coll = await client.post(
        "/collections", json={"name": "Old Name"}, headers=headers
    )
    coll_id = coll.json()["id"]

    resp = await client.patch(
        f"/collections/{coll_id}", json={"name": "New Name"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_collection(client: AsyncClient):
    headers = await _auth_header(client, "del@example.com")
    coll = await client.post(
        "/collections", json={"name": "To Delete"}, headers=headers
    )
    coll_id = coll.json()["id"]

    resp = await client.delete(f"/collections/{coll_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/collections/{coll_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_collections_isolated_between_users(client: AsyncClient):
    headers_a = await _auth_header(client, "usera@example.com")
    headers_b = await _auth_header(client, "userb@example.com")

    await client.post("/collections", json={"name": "A's collection"}, headers=headers_a)

    resp = await client.get("/collections", headers=headers_b)
    assert resp.json() == []
