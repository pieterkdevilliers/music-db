"""Roon Core connection manager for library probe/import.

The roonapi library is synchronous and thread-based, so all blocking calls
must be run via run_in_executor when called from FastAPI async routes.

Pairing flow (one-time per Roon Core):
  1. Call connect(host, port) — starts the socket thread
  2. User opens Roon > Settings > Extensions and clicks Enable
  3. Roon issues an auth token; roon.token becomes non-None
  4. Token is saved to TOKEN_PATH for future runs (no re-pairing needed)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from pathlib import Path

from roonapi import RoonApi

logger = logging.getLogger(__name__)

TOKEN_PATH = Path("/app/data/roon_token.json")
_TRACK_RE = re.compile(r"^\d+\.\s+(.+)$")

APPINFO = {
    "extension_id": "music_db_importer",
    "display_name": "Music DB Importer",
    "display_version": "1.0.0",
    "publisher": "music-db",
    "email": "noreply@music-db",
}

_roon: RoonApi | None = None
_lock = threading.Lock()
_last_mb_request: float = 0.0   # monotonic timestamp of last MusicBrainz search
_MB_MIN_INTERVAL = 1.1           # seconds — MusicBrainz rate limit is 1 req/sec

_import_job: dict = {
    "status": "idle",   # idle | starting | running | done | cancelled | error
    "total": 0,
    "done": 0,
    "imported": 0,
    "updated": 0,
    "skipped": 0,
    "errors": 0,
    "error_list": [],
    "collection_id": None,
    "cancel_requested": False,
}


def _load_token() -> str | None:
    try:
        data = json.loads(TOKEN_PATH.read_text())
        return data.get("token")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def _save_token(token: str) -> None:
    TOKEN_PATH.write_text(json.dumps({"token": token}))


def connect(host: str, port: int) -> None:
    """Start a (non-blocking) connection attempt to the Roon Core.

    The socket thread runs in the background.  Call get_status() to poll
    whether authorization has completed.
    """
    global _roon
    token = _load_token()
    with _lock:
        # Close any existing connection first
        if _roon is not None:
            try:
                _roon._exit = True
            except Exception:
                pass
        _roon = RoonApi(
            APPINFO,
            token,
            host,
            port,
            blocking_init=False,  # don't block; let user approve in Roon UI
        )
    logger.info("Roon connection initiated to %s:%s", host, port)


def get_status() -> dict:
    """Return current connection state.

    'connected' is True only when the TCP handshake with Roon Core has
    actually completed (evidenced by core_name being set by the library).
    'authorized' additionally requires a valid auth token.  This prevents
    a stale cached token from being reported as authorized when the socket
    is not yet connected.
    """
    with _lock:
        if _roon is None:
            return {"connected": False, "authorized": False, "core_name": None}
        core_name = _roon.core_name   # set by roonapi only after successful handshake
        token = _roon.token
        actually_connected = core_name is not None
        if token and actually_connected:
            _save_token(token)
        return {
            "connected": actually_connected,
            "authorized": actually_connected and bool(token),
            "core_name": core_name,
        }


def probe(count: int = 3) -> dict:
    """Browse the Roon library and return raw data for the first `count` albums.

    Returns a dict with:
      - albums: list of top-level browse items (title, subtitle, image_key, item_key)
      - first_album_detail: raw browse result when drilling into the first album
    """
    with _lock:
        roon = _roon

    if roon is None:
        raise RuntimeError("Not connected to Roon Core")
    if not roon.token:
        raise RuntimeError("Roon Core not yet authorized — approve the extension in Roon > Settings > Extensions")

    # 1. Browse the Albums hierarchy
    browse_result = roon.browse_browse({
        "hierarchy": "albums",
        "count": count,
        "pop_all": True,
    })
    if not browse_result:
        raise RuntimeError("Roon browse returned no result — is the library loaded?")

    load_result = roon.browse_load({
        "hierarchy": "albums",
        "count": count,
        "offset": 0,
    })

    albums = load_result.get("items", []) if load_result else []

    # 2. Drill into the first album for full detail
    first_album_detail = None
    if albums and albums[0].get("item_key"):
        detail_browse = roon.browse_browse({
            "hierarchy": "albums",
            "item_key": albums[0]["item_key"],
        })
        detail_load = roon.browse_load({
            "hierarchy": "albums",
            "count": 50,
            "offset": 0,
        })
        first_album_detail = {
            "browse": detail_browse,
            "items": detail_load.get("items", []) if detail_load else [],
        }

    return {
        "browse_result": browse_result,
        "albums": albums,
        "first_album_detail": first_album_detail,
    }


# ---------------------------------------------------------------------------
# Bulk import — synchronous helpers (called via run_in_executor)
# ---------------------------------------------------------------------------

def _parse_tracks(items: list[dict]) -> list[str]:
    """Extract track titles from album browse items, stripping the 'N. ' prefix."""
    tracks = []
    for item in items:
        m = _TRACK_RE.match(item.get("title", ""))
        if m:
            tracks.append(m.group(1))
    return tracks


def _sync_load_page(roon: RoonApi, offset: int, page_size: int) -> tuple[list[dict], int]:
    """Load one page from the albums list hierarchy.

    Resets to albums root when offset == 0.  Returns (items, total_count).
    total_count is only meaningful when offset == 0.
    """
    total = 0
    if offset == 0:
        browse_result = roon.browse_browse({"hierarchy": "albums", "pop_all": True})
        total = (browse_result or {}).get("list", {}).get("count", 0)
    load_result = roon.browse_load({
        "hierarchy": "albums",
        "count": page_size,
        "offset": offset,
    })
    items = (load_result or {}).get("items", [])
    return items, total


def _sync_fetch_detail(
    roon: RoonApi, item_key: str, image_key: str | None
) -> tuple[list[str], bytes | None]:
    """Drill into an album and collect tracks + artwork.

    Resets the browse state to the albums root first so that multiple
    sequential calls always start from a known position.
    """
    # Navigate to the album's track listing
    roon.browse_browse({"hierarchy": "albums", "pop_all": True})
    roon.browse_browse({"hierarchy": "albums", "item_key": item_key})

    tracks: list[str] = []
    offset = 0
    while True:
        load_result = roon.browse_load({
            "hierarchy": "albums",
            "count": 100,
            "offset": offset,
        })
        items = (load_result or {}).get("items", [])
        tracks.extend(_parse_tracks(items))
        if len(items) < 100:
            break
        offset += 100

    # Download artwork via Roon image server
    image_bytes: bytes | None = None
    if image_key:
        try:
            raw = roon.get_image(image_key, scale="fit", width=600, height=600)
            if raw is None:
                logger.debug("Roon get_image returned None for key %s", image_key)
            elif isinstance(raw, (bytes, bytearray)):
                if len(raw) > 0:
                    image_bytes = bytes(raw)
                else:
                    logger.debug("Roon get_image returned empty bytes for key %s", image_key)
            else:
                logger.debug(
                    "Roon get_image returned unexpected type %s for key %s",
                    type(raw).__name__, image_key,
                )
        except Exception as exc:
            logger.debug("Roon get_image failed for key %s: %s", image_key, exc)

    return tracks, image_bytes


# ---------------------------------------------------------------------------
# Bulk import — async coroutine
# ---------------------------------------------------------------------------

async def run_import(
    session_factory,
    collection_id: int | None = None,
) -> None:
    """Import all albums from the connected Roon library into the database.

    Existing albums (matched by title + artist) are updated rather than
    skipped: tracks are refreshed and artwork is downloaded if not already set.
    If collection_id is supplied every processed album is added to that
    collection (duplicates are silently ignored).

    Designed to run as a background asyncio.Task.  Progress is tracked in the
    module-level _import_job dict and can be read via get_progress().
    """
    from app.models.album import Album
    from app.models.collection_album import CollectionAlbum
    from app.schemas.album import AlbumCreate
    from app.services.album import create_album
    from app.services.musicbrainz import (
        ALBUM_ART_DIR,
        download_cover_art,
        search_releases,
    )
    from sqlalchemy import select

    global _import_job, _last_mb_request

    with _lock:
        roon = _roon

    if roon is None or not roon.token:
        _import_job["status"] = "error"
        _import_job["error_list"].append("Not connected or not authorized")
        return

    loop = asyncio.get_running_loop()
    page_size = 100

    async def _link_to_collection(db, album_id: int) -> None:
        """Add album to the target collection if not already a member."""
        if collection_id is None:
            return
        exists = (await db.execute(
            select(CollectionAlbum).where(
                CollectionAlbum.collection_id == collection_id,
                CollectionAlbum.album_id == album_id,
            )
        )).scalar_one_or_none()
        if exists is None:
            db.add(CollectionAlbum(collection_id=collection_id, album_id=album_id))
            await db.commit()

    async def _mb_art_fallback(album_id: int, title: str, artist: str) -> bool:
        """Search MusicBrainz and download cover art if found.

        Respects the 1 req/sec rate limit by sleeping only as long as necessary.
        Returns True if art was successfully saved.
        """
        global _last_mb_request
        elapsed = time.monotonic() - _last_mb_request
        if elapsed < _MB_MIN_INTERVAL:
            await asyncio.sleep(_MB_MIN_INTERVAL - elapsed)
        _last_mb_request = time.monotonic()

        try:
            candidates = await search_releases(title, artist)
            if not candidates:
                return False
            mbid = candidates[0].get("mbid")
            if not mbid:
                return False

            art_filename = f"{album_id}.jpg"
            dest = ALBUM_ART_DIR / art_filename
            downloaded = await download_cover_art(mbid, dest)
            if downloaded:
                async with session_factory() as db:
                    db_row = (await db.execute(
                        select(Album).where(Album.id == album_id)
                    )).scalar_one()
                    db_row.art_path = art_filename
                    await db.commit()
                logger.debug("MB art saved for album %d (%s)", album_id, title)
                return True
        except Exception as exc:
            logger.debug("MB art fallback failed for album %d: %s", album_id, exc)
        return False

    try:
        _import_job["status"] = "running"

        # ── Phase 1: collect the full album list ─────────────────────────────
        all_items: list[dict] = []
        offset = 0

        while True:
            if _import_job["cancel_requested"]:
                _import_job["status"] = "cancelled"
                return

            off = offset
            items, total = await loop.run_in_executor(
                None, lambda o=off: _sync_load_page(roon, o, page_size)
            )

            if offset == 0 and total:
                _import_job["total"] = total

            all_items.extend(items)
            logger.info(
                "Roon import listing: %d items so far (reported total: %s)",
                len(all_items), _import_job["total"] or "?",
            )

            if len(items) < page_size:
                break
            offset += page_size

        # Use actual item count as total (more accurate than the API-reported count)
        _import_job["total"] = len(all_items)
        logger.info("Roon import: %d albums to process", _import_job["total"])

        # ── Phase 2: import each album ────────────────────────────────────────
        for album_item in all_items:
            if _import_job["cancel_requested"]:
                _import_job["status"] = "cancelled"
                return

            # Yield control so other handlers can run
            await asyncio.sleep(0)

            title = (album_item.get("title") or "").strip()
            artist = (album_item.get("subtitle") or "").strip()
            item_key = album_item.get("item_key") or ""
            image_key = album_item.get("image_key")

            # Skip action items (e.g. "Play Album") that have no item_key
            if not title or not item_key:
                _import_job["done"] += 1
                _import_job["skipped"] += 1
                continue

            try:
                # Fetch tracks + artwork outside the DB session to keep
                # the session open as briefly as possible
                ik, imgk = item_key, image_key
                tracks, image_bytes = await loop.run_in_executor(
                    None,
                    lambda i=ik, k=imgk: _sync_fetch_detail(roon, i, k),
                )

                album_id_val: int
                has_art: bool

                async with session_factory() as db:
                    existing = (await db.execute(
                        select(Album).where(
                            Album.title.ilike(title),
                            Album.artist.ilike(artist),
                        )
                    )).scalar_one_or_none()

                    if existing is not None:
                        # Update existing album: refresh tracks and fill art if absent
                        existing.tracks = tracks
                        if image_bytes and not existing.art_path:
                            art_filename = f"{existing.id}.jpg"
                            (ALBUM_ART_DIR / art_filename).write_bytes(image_bytes)
                            existing.art_path = art_filename
                        has_art = bool(existing.art_path)
                        await db.commit()
                        await _link_to_collection(db, existing.id)
                        album_id_val = existing.id
                        _import_job["updated"] += 1

                    else:
                        # Create new album record
                        schema = AlbumCreate(title=title, artist=artist, tracks=tracks)
                        album = await create_album(db, schema)

                        if image_bytes:
                            art_filename = f"{album.id}.jpg"
                            (ALBUM_ART_DIR / art_filename).write_bytes(image_bytes)
                            db_row = (await db.execute(
                                select(Album).where(Album.id == album.id)
                            )).scalar_one()
                            db_row.art_path = art_filename
                            await db.commit()
                            has_art = True
                        else:
                            has_art = False

                        await _link_to_collection(db, album.id)
                        album_id_val = album.id
                        _import_job["imported"] += 1

                # MusicBrainz art fallback — only for albums that have no art yet
                if not has_art:
                    await _mb_art_fallback(album_id_val, title, artist)

            except Exception as exc:
                logger.warning(
                    "Roon import: failed '%s' by '%s': %s", title, artist, exc
                )
                _import_job["errors"] += 1
                msg = f"{title} — {exc}"
                if len(_import_job["error_list"]) >= 50:
                    _import_job["error_list"] = _import_job["error_list"][-49:]
                _import_job["error_list"].append(msg)

            finally:
                _import_job["done"] += 1

        _import_job["status"] = "done"
        logger.info(
            "Roon import complete: imported=%d updated=%d skipped=%d errors=%d",
            _import_job["imported"], _import_job["updated"],
            _import_job["skipped"], _import_job["errors"],
        )

    except Exception as exc:
        logger.error("Roon import crashed: %s", exc)
        _import_job["status"] = "error"
        _import_job["error_list"].append(str(exc))


def reset_import_job(collection_id: int | None = None) -> None:
    """Reset the job state dict before starting a new import."""
    global _import_job
    _import_job = {
        "status": "starting",
        "total": 0,
        "done": 0,
        "imported": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "error_list": [],
        "collection_id": collection_id,
        "cancel_requested": False,
    }


def get_progress() -> dict:
    """Return a snapshot of the current import job state."""
    return dict(_import_job)


def cancel_import() -> None:
    """Request cancellation of the running import."""
    _import_job["cancel_requested"] = True
