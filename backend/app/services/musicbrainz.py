from __future__ import annotations

from pathlib import Path

import httpx

MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
ALBUM_ART_DIR = Path("/app/data/album_art")
HEADERS = {
    "User-Agent": "MusicDB/1.0 (personal music library)",
    "Accept": "application/json",
}


def _join_artist_credits(artist_credits: list[dict]) -> str:
    """Flatten MusicBrainz artist-credit list into a display name."""
    parts = []
    for credit in artist_credits:
        if isinstance(credit, dict) and "artist" in credit:
            parts.append(credit.get("name") or credit["artist"].get("name", ""))
        elif isinstance(credit, str):
            parts.append(credit)
    return "".join(parts).strip()


async def search_releases(title: str, artist: str) -> list[dict]:
    """Search MusicBrainz for releases matching title and artist.

    Returns a simplified list of candidates suitable for display.
    """
    query = f'release:"{title}" AND artist:"{artist}"'
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(
            f"{MB_BASE}/release",
            params={"query": query, "fmt": "json", "limit": 10},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for r in data.get("releases", []):
        artist_display = _join_artist_credits(r.get("artist-credit", []))
        label = None
        label_info = r.get("label-info", [])
        if label_info and isinstance(label_info, list):
            first = label_info[0]
            if isinstance(first, dict) and first.get("label"):
                label = first["label"].get("name")

        year = None
        date = r.get("date", "")
        if date and len(date) >= 4:
            try:
                year = int(date[:4])
            except ValueError:
                pass

        track_count = r.get("track-count", 0)
        country = r.get("country") or None

        results.append(
            {
                "mbid": r["id"],
                "title": r.get("title", ""),
                "artist": artist_display,
                "year": year,
                "label": label,
                "country": country,
                "track_count": track_count,
            }
        )
    return results


async def get_release(mbid: str) -> dict:
    """Fetch full release details for pre-populating the album form.

    Returns: title, artist, year, label, tracks (list of track titles).
    """
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(
            f"{MB_BASE}/release/{mbid}",
            params={"inc": "recordings+artist-credits+labels", "fmt": "json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

    artist_display = _join_artist_credits(data.get("artist-credit", []))

    label = None
    label_info = data.get("label-info", [])
    if label_info and isinstance(label_info, list):
        first = label_info[0]
        if isinstance(first, dict) and first.get("label"):
            label = first["label"].get("name")

    year = None
    date = data.get("date", "")
    if date and len(date) >= 4:
        try:
            year = int(date[:4])
        except ValueError:
            pass

    tracks: list[str] = []
    for medium in data.get("media", []):
        for track in medium.get("tracks", []):
            title = track.get("title") or (
                track.get("recording", {}).get("title", "")
            )
            if title:
                tracks.append(title)

    return {
        "mbid": mbid,
        "title": data.get("title", ""),
        "artist": artist_display,
        "year": year,
        "label": label,
        "tracks": tracks,
    }


async def download_cover_art(mbid: str, dest_path: Path) -> bool:
    """Download the front cover art from the Cover Art Archive.

    Saves the image to dest_path. Returns True if downloaded, False if not found.
    """
    url = f"{CAA_BASE}/release/{mbid}/front"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            return True
    except httpx.HTTPError:
        return False
