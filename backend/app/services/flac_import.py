"""Audio file scanner for bulk library import.

Scans a directory tree for audio files (FLAC, MP3, etc.), groups them by album
directory, extracts metadata via mutagen, and imports albums into the database.

The scan path must be accessible inside the Docker container.  Mount your
music library as a read-only volume in docker-compose.yml, e.g.:

    services:
      backend:
        volumes:
          - /mnt/music:/music:ro

Then enter /music as the scan path in the UI.

Behaviour mirrors the Roon importer:
  - Existing albums (matched by title + artist) are updated (tracks refreshed,
    release year / label / art filled in if previously absent).
  - New albums are created.
  - If no embedded or folder art is found, MusicBrainz Cover Art Archive is
    tried as a fallback (rate-limited to 1 req/sec).
  - All processed albums can optionally be added to a collection.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = frozenset({".flac", ".mp3", ".m4a", ".aiff", ".aif", ".ogg", ".wav"})

# Common cover-art filenames to look for inside the album directory
_COVER_NAMES = [
    "cover.jpg", "cover.jpeg",
    "folder.jpg", "folder.jpeg",
    "front.jpg", "front.jpeg",
    "albumart.jpg", "albumart.jpeg",
    "AlbumArt.jpg",
    "cover.png", "folder.png",
]

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
    "root_path": None,
    "cancel_requested": False,
}

_last_mb_request: float = 0.0
_MB_MIN_INTERVAL = 1.1   # MusicBrainz rate limit: 1 req/sec


# ---------------------------------------------------------------------------
# Synchronous helpers (called via run_in_executor)
# ---------------------------------------------------------------------------

def _find_album_dirs(root: Path) -> list[Path]:
    """Return all directories that directly contain at least one audio file."""
    album_dirs: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(str(root)):
        if any(Path(f).suffix.lower() in AUDIO_EXTENSIONS for f in filenames):
            album_dirs.append(Path(dirpath))
    return sorted(album_dirs)


def _get_tag(tags: object, *keys: str) -> str | None:
    """Return the first non-empty value for any of the given tag keys.

    Tries each key as-is, uppercased, and lowercased to handle both Vorbis
    Comment (FLAC/OGG) and ID3-style (MP3) tag naming conventions.
    """
    if tags is None:
        return None
    for k in keys:
        for variant in (k, k.upper(), k.lower()):
            val = getattr(tags, "get", lambda *_: None)(variant)
            if val:
                v = val[0] if isinstance(val, list) else val
                s = str(v).strip()
                if s:
                    return s
    return None


def _scan_album_dir(dir_path: Path) -> dict | None:
    """Synchronous: extract album metadata from a directory of audio files.

    Returns a dict with keys:
        title, artist, release_year, record_label, tracks, image_bytes

    Returns None if no audio files are found or mutagen is unavailable.
    """
    try:
        from mutagen import File as MutaFile
        from mutagen.flac import FLAC
    except ImportError:
        logger.error("mutagen not installed — rebuild the Docker image after adding it to pyproject.toml")
        return None

    audio_files = sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not audio_files:
        return None

    flac_files = [f for f in audio_files if f.suffix.lower() == ".flac"]

    # ── Album-level metadata from the first audio file ──────────────────────
    first_audio = MutaFile(str(audio_files[0]))
    tags = getattr(first_audio, "tags", None) if first_audio else None

    title = _get_tag(tags, "album") or dir_path.name
    artist = (
        _get_tag(tags, "albumartist", "album_artist", "TPE2")
        or _get_tag(tags, "artist", "TPE1")
        or "Unknown"
    )
    year_str = _get_tag(tags, "date", "year", "TDRC")
    release_year = int(year_str[:4]) if year_str and year_str[:4].isdigit() else None
    record_label = _get_tag(tags, "organization", "label", "publisher", "TPUB")

    # ── Track titles ─────────────────────────────────────────────────────────
    tracks: list[str] = []
    for af in audio_files:
        try:
            audio = MutaFile(str(af))
            t_tags = getattr(audio, "tags", None) if audio else None
            track_title = _get_tag(t_tags, "title", "TIT2") or af.stem
            tracks.append(track_title)
        except Exception:
            tracks.append(af.stem)

    # ── Artwork: embedded FLAC picture → directory image files ───────────────
    image_bytes: bytes | None = None

    if flac_files:
        try:
            flac = FLAC(str(flac_files[0]))
            pics = flac.pictures
            # Prefer picture type 3 (Front Cover), fall back to first picture
            front = next((p for p in pics if p.type == 3), None)
            pic = front or (pics[0] if pics else None)
            if pic and pic.data:
                image_bytes = pic.data
        except Exception:
            pass

    if not image_bytes:
        # Try known cover-art filenames
        for name in _COVER_NAMES:
            art_file = dir_path / name
            if art_file.exists():
                try:
                    image_bytes = art_file.read_bytes()
                    break
                except Exception:
                    pass

    if not image_bytes:
        # Last resort: any JPEG or PNG in the directory
        for f in sorted(dir_path.iterdir()):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"} and f.is_file():
                try:
                    image_bytes = f.read_bytes()
                    break
                except Exception:
                    pass

    return {
        "title": title,
        "artist": artist,
        "release_year": release_year,
        "record_label": record_label,
        "tracks": tracks,
        "image_bytes": image_bytes,
    }


# ---------------------------------------------------------------------------
# Bulk import — async coroutine
# ---------------------------------------------------------------------------

async def run_import(
    session_factory,
    root_path: str,
    collection_id: int | None = None,
) -> None:
    """Scan root_path for audio files and import albums into the database."""
    from app.models.album import Album
    from app.models.collection_album import CollectionAlbum
    from app.schemas.album import AlbumCreate
    from app.services.album import create_album, get_or_create_record_label
    from app.services.musicbrainz import ALBUM_ART_DIR, download_cover_art, search_releases
    from sqlalchemy import select

    global _import_job, _last_mb_request

    loop = asyncio.get_running_loop()
    root = Path(root_path)

    if not root.is_dir():
        _import_job["status"] = "error"
        _import_job["error_list"].append(f"Directory not found or not accessible: {root_path}")
        return

    # ── Helpers (close over session_factory / collection_id) ─────────────────

    async def _link_to_collection(db, album_id: int) -> None:
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

        # ── Phase 1: discover album directories ──────────────────────────────
        album_dirs = await loop.run_in_executor(None, lambda: _find_album_dirs(root))
        _import_job["total"] = len(album_dirs)
        logger.info("File import: found %d directories under %s", len(album_dirs), root_path)

        # ── Phase 2: process each directory ──────────────────────────────────
        for dir_path in album_dirs:
            if _import_job["cancel_requested"]:
                _import_job["status"] = "cancelled"
                return

            await asyncio.sleep(0)  # yield control to event loop

            try:
                dp = dir_path
                data = await loop.run_in_executor(None, lambda d=dp: _scan_album_dir(d))

                if data is None:
                    _import_job["skipped"] += 1
                    continue

                title = data["title"]
                artist = data["artist"]
                tracks = data["tracks"]
                image_bytes = data["image_bytes"]

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
                        # Update existing album
                        existing.tracks = tracks
                        if data["release_year"] and not existing.release_year:
                            existing.release_year = data["release_year"]
                        if data["record_label"] and not existing.record_label_id:
                            label = await get_or_create_record_label(db, data["record_label"])
                            existing.record_label_id = label.id
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
                        # Create new album
                        schema = AlbumCreate(
                            title=title,
                            artist=artist,
                            tracks=tracks,
                            release_year=data["release_year"],
                            record_label=data["record_label"],
                        )
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

                # MusicBrainz art fallback — only if no local art was found
                if not has_art:
                    await _mb_art_fallback(album_id_val, title, artist)

            except Exception as exc:
                logger.warning("File import: failed directory '%s': %s", dir_path, exc)
                _import_job["errors"] += 1
                msg = f"{dir_path.name} — {exc}"
                if len(_import_job["error_list"]) >= 50:
                    _import_job["error_list"] = _import_job["error_list"][-49:]
                _import_job["error_list"].append(msg)

            finally:
                _import_job["done"] += 1

        _import_job["status"] = "done"
        logger.info(
            "File import complete: imported=%d updated=%d skipped=%d errors=%d",
            _import_job["imported"], _import_job["updated"],
            _import_job["skipped"], _import_job["errors"],
        )

    except Exception as exc:
        logger.error("File import crashed: %s", exc)
        _import_job["status"] = "error"
        _import_job["error_list"].append(str(exc))


def reset_import_job(root_path: str = "", collection_id: int | None = None) -> None:
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
        "root_path": root_path,
        "cancel_requested": False,
    }


def get_progress() -> dict:
    return dict(_import_job)


def cancel_import() -> None:
    _import_job["cancel_requested"] = True
