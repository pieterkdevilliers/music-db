import pytest
from httpx import AsyncClient


async def _auth_header(client: AsyncClient, email: str = "user@example.com") -> dict:
    await client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    login = await client.post(
        "/auth/login", data={"username": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


ALBUM_PAYLOAD = {
    "title": "Led Zeppelin IV",
    "artist": "Led Zeppelin",
    "release_year": 1971,
    "producer": "Jimmy Page",
    "record_label": "Atlantic",
    "tracks": ["Black Dog", "Rock and Roll", "Stairway to Heaven"],
    "musicians": [
        {"musician_name": "John Bonham", "instrument": "drums"},
        {"musician_name": "Jimmy Page", "instrument": "guitar"},
        {"musician_name": "Robert Plant", "instrument": "vocals"},
        {"musician_name": "John Paul Jones", "instrument": "bass"},
    ],
}


@pytest.mark.asyncio
async def test_create_album(client: AsyncClient):
    headers = await _auth_header(client)
    resp = await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Led Zeppelin IV"
    assert data["record_label"] == "Atlantic"
    assert len(data["musicians"]) == 4
    assert data["tracks"] == ["Black Dog", "Rock and Roll", "Stairway to Heaven"]


@pytest.mark.asyncio
async def test_get_album(client: AsyncClient):
    headers = await _auth_header(client, "get@example.com")
    create = await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    album_id = create.json()["id"]

    resp = await client.get(f"/albums/{album_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == album_id


@pytest.mark.asyncio
async def test_filter_by_musician_and_instrument(client: AsyncClient):
    headers = await _auth_header(client, "filter@example.com")
    create = await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    album_id = create.json()["id"]

    # Find John Bonham's musician id
    musicians = await client.get("/musicians?search=Bonham", headers=headers)
    bonham = musicians.json()[0]
    musician_id = bonham["id"]

    # Filter albums by drummer
    resp = await client.get(
        f"/albums?musician_id={musician_id}&instrument=drums", headers=headers
    )
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()]
    assert album_id in ids


@pytest.mark.asyncio
async def test_update_album(client: AsyncClient):
    headers = await _auth_header(client, "update@example.com")
    create = await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    album_id = create.json()["id"]

    resp = await client.patch(
        f"/albums/{album_id}",
        json={"title": "IV (Remastered)"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "IV (Remastered)"


@pytest.mark.asyncio
async def test_delete_album(client: AsyncClient):
    headers = await _auth_header(client, "delete@example.com")
    create = await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    album_id = create.json()["id"]

    resp = await client.delete(f"/albums/{album_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/albums/{album_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_musician_get_or_create(client: AsyncClient):
    """The same musician name should resolve to one row even when added via two albums."""
    headers = await _auth_header(client, "dedup@example.com")
    payload2 = {**ALBUM_PAYLOAD, "title": "Physical Graffiti", "release_year": 1975}
    await client.post("/albums", json=ALBUM_PAYLOAD, headers=headers)
    await client.post("/albums", json=payload2, headers=headers)

    musicians = await client.get("/musicians?search=John Bonham", headers=headers)
    assert len(musicians.json()) == 1
