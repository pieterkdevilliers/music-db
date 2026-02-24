"""AI-powered album enrichment using the Anthropic Claude API.

For each album, Claude is prompted with the title, artist, and release year
and asked to return structured information about:
  - Producer
  - Musicians (name + instrument)
  - Personnel (name + role: engineer, mix engineer, etc.)
  - Other details (recording studio, chart positions, etc.)

Enrichment is additive (merge/append only):
  - Producer is only set when the field is currently null.
  - Musicians are appended only when the musician name is not already on the album.
    Dedup is by name only (not instrument) so one musician does not appear twice.
  - Personnel are appended only for new (person_name, role) pairs.
  - Other details are appended only for new (detail_name, detail_type) pairs.

Existing DB entity names (musicians, persons, details) are passed to Claude so it
can normalise spelling to match existing records (preventing "Phil Collen" and
"Philip Collen" becoming two separate DB rows for the same person).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detail import Detail
from app.models.musician import Musician
from app.models.person import Person
from app.schemas.album import AlbumDetailInput, AlbumMusicianInput, AlbumPersonnelInput, AlbumUpdate

logger = logging.getLogger(__name__)

_enrichment_job: dict = {
    "status": "idle",
    "total": 0,
    "done": 0,
    "enriched": 0,
    "skipped": 0,
    "errors": 0,
    "error_list": [],
    "cancel_requested": False,
    "current_album": None,
}

_ENRICHMENT_TOOL = {
    "name": "album_enrichment",
    "description": "Structured album credits and metadata",
    "input_schema": {
        "type": "object",
        "properties": {
            "producer": {
                "type": "string",
                "description": "Main album producer name, or empty string if unknown",
            },
            "musicians": {
                "type": "array",
                "description": "List of musicians who performed on the album",
                "items": {
                    "type": "object",
                    "properties": {
                        "musician_name": {"type": "string"},
                        "instrument": {"type": "string"},
                    },
                    "required": ["musician_name", "instrument"],
                },
            },
            "personnel": {
                "type": "array",
                "description": "Production/technical personnel on the album",
                "items": {
                    "type": "object",
                    "properties": {
                        "person_name": {"type": "string"},
                        "role": {"type": "string"},
                    },
                    "required": ["person_name", "role"],
                },
            },
            "other_details": {
                "type": "array",
                "description": (
                    "Additional album details such as studios. "
                    "Do NOT include chart positions — these are frequently inaccurate."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "detail_name": {
                            "type": "string",
                            "description": "The value, e.g. 'Abbey Road Studios' or 'Sterling Sound'",
                        },
                        "detail_type": {
                            "type": "string",
                            "description": "Category, e.g. 'Recording Studio' or 'Mastering Studio'",
                        },
                    },
                    "required": ["detail_name", "detail_type"],
                },
            },
        },
        "required": ["producer", "musicians", "personnel", "other_details"],
    },
}


def _build_prompt(
    title: str,
    artist: str,
    release_year: int | None,
    known_musicians: list[str],
    known_persons: list[str],
    known_details: list[str],
) -> str:
    year_str = f" ({release_year})" if release_year else ""
    lines = [
        f'Provide accurate credits for the album "{title}" by {artist}{year_str}.',
        "",
        "For musicians: list every performer and their instrument(s).",
        "For personnel: include roles such as Producer, Engineer, Assistant Engineer, "
        "Recording Engineer, Mix Engineer, Mastering Engineer, Assistant Producer, "
        "and any other credited roles.",
        "For other_details: include Recording Studio and Mastering Studio/Company only. "
        "Do NOT include chart positions (UK, US, or any other) — they are hard to verify "
        "and frequently wrong.",
        "",
        "ACCURACY IS CRITICAL. Only return data you are certain of from the album's "
        "liner notes or well-documented sources. It is far better to return an empty "
        "array than to include a single incorrect entry. Do not guess or infer.",
        "",
    ]
    if known_musicians:
        lines.append(
            "Known musicians already in the database (use the exact spelling if you "
            f"identify the same person): {', '.join(known_musicians[:200])}"
        )
    if known_persons:
        lines.append(
            "Known personnel already in the database (use the exact spelling if you "
            f"identify the same person): {', '.join(known_persons[:200])}"
        )
    if known_details:
        lines.append(
            "Known detail values already in the database (use the exact spelling if you "
            f"identify the same value): {', '.join(known_details[:200])}"
        )
    return "\n".join(lines)


def _call_claude(
    title: str,
    artist: str,
    release_year: int | None,
    known_musicians: list[str],
    known_persons: list[str],
    known_details: list[str],
) -> dict[str, Any]:
    """Synchronous Claude API call — run via run_in_executor from async code."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = _build_prompt(title, artist, release_year, known_musicians, known_persons, known_details)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=(
            "You are a precise music database assistant. Your only job is to return "
            "verified album credits. Never fabricate, infer, or guess data. "
            "If you are not certain a fact appears in the album's official liner notes "
            "or is documented from a highly reliable source, omit it entirely. "
            "Returning an empty array is always correct; returning wrong data is never acceptable."
        ),
        tools=[_ENRICHMENT_TOOL],
        tool_choice={"type": "tool", "name": "album_enrichment"},
        messages=[{"role": "user", "content": prompt}],
    )
    # With tool_choice forced, the first content block is always the tool_use block
    for block in message.content:
        if block.type == "tool_use" and block.name == "album_enrichment":
            return block.input  # type: ignore[return-value]
    return {}


async def _get_known_names(db: AsyncSession) -> tuple[list[str], list[str], list[str]]:
    """Fetch all existing entity names from the DB for the Claude prompt."""
    musicians = list((await db.execute(select(Musician.name).order_by(Musician.name))).scalars().all())
    persons = list((await db.execute(select(Person.name).order_by(Person.name))).scalars().all())
    details = list((await db.execute(select(Detail.name).order_by(Detail.name))).scalars().all())
    return musicians, persons, details


def _merge_musicians(
    existing: list[dict],
    new: list[dict],
) -> list[dict]:
    """Append musicians from `new` whose name is not already in `existing`.

    Deduplication is by musician_name only (case-insensitive) so the same
    person never appears twice on an album regardless of instrument differences.
    """
    existing_names = {m["musician_name"].lower() for m in existing}
    merged = list(existing)
    for m in new:
        if m["musician_name"].lower() not in existing_names:
            merged.append(m)
            existing_names.add(m["musician_name"].lower())
    return merged


def _merge_personnel(
    existing: list[dict],
    new: list[dict],
) -> list[dict]:
    """Append personnel from `new` whose (person_name, role) pair is not already present."""
    existing_keys = {(p["person_name"].lower(), p["role"].lower()) for p in existing}
    merged = list(existing)
    for p in new:
        key = (p["person_name"].lower(), p["role"].lower())
        if key not in existing_keys:
            merged.append(p)
            existing_keys.add(key)
    return merged


def _merge_details(
    existing: list[dict],
    new: list[dict],
) -> list[dict]:
    """Append details from `new` whose (detail_name, detail_type) pair is not already present."""
    existing_keys = {(d["detail_name"].lower(), d["detail_type"].lower()) for d in existing}
    merged = list(existing)
    for d in new:
        key = (d["detail_name"].lower(), d["detail_type"].lower())
        if key not in existing_keys:
            merged.append(d)
            existing_keys.add(key)
    return merged


async def enrich_album(db: AsyncSession, album_id: int) -> bool:
    """Enrich a single album with AI-sourced data.

    Returns True if the album was updated, False if skipped or not found.
    Raises on Claude API or DB errors.
    """
    from app.services.album import get_album_full, update_album

    album = await get_album_full(db, album_id)
    if album is None:
        return False

    known_musicians, known_persons, known_details = await _get_known_names(db)

    loop = asyncio.get_running_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: _call_claude(
            album.title,
            album.artist,
            album.release_year,
            known_musicians,
            known_persons,
            known_details,
        ),
    )

    if not raw:
        return False

    # Build existing data dicts for merging
    existing_musicians = [
        {"musician_name": link._musician_obj.name, "instrument": link.instrument}
        for link in album.album_musician_links
        if link._musician_obj is not None
    ]
    existing_personnel = [
        {"person_name": link._person_obj.name, "role": link.role}
        for link in album.album_personnel_links
        if link._person_obj is not None
    ]
    existing_details = [
        {"detail_name": link._detail_obj.name, "detail_type": link.detail_type}
        for link in album.album_detail_links
        if link._detail_obj is not None
    ]

    # Merge enrichment results with existing data
    merged_musicians = _merge_musicians(existing_musicians, raw.get("musicians", []))
    merged_personnel = _merge_personnel(existing_personnel, raw.get("personnel", []))
    merged_details = _merge_details(existing_details, raw.get("other_details", []))

    # Build update schema — only set producer if currently null
    update = AlbumUpdate(
        producer=raw.get("producer") or None if not album.producer else None,
        musicians=[AlbumMusicianInput(**m) for m in merged_musicians],
        personnel=[AlbumPersonnelInput(**p) for p in merged_personnel],
        other_details=[AlbumDetailInput(**d) for d in merged_details],
    )

    await update_album(db, album_id, update)
    return True


async def run_album_enrichment(session_factory, album_id: int) -> None:
    """Background task: enrich a single album."""
    global _enrichment_job
    _enrichment_job = {
        "status": "running",
        "total": 1,
        "done": 0,
        "enriched": 0,
        "skipped": 0,
        "errors": 0,
        "error_list": [],
        "cancel_requested": False,
        "current_album": None,
    }
    try:
        async with session_factory() as db:
            from app.models.album import Album
            row = (await db.execute(select(Album).where(Album.id == album_id))).scalar_one_or_none()
            label = f"{row.title} — {row.artist}" if row else f"album {album_id}"
        _enrichment_job["current_album"] = label

        async with session_factory() as db:
            enriched = await enrich_album(db, album_id)

        if enriched:
            _enrichment_job["enriched"] += 1
        else:
            _enrichment_job["skipped"] += 1
    except Exception as exc:
        logger.error("Enrichment failed for album %d: %s", album_id, exc)
        _enrichment_job["errors"] += 1
        _enrichment_job["error_list"].append(str(exc))
    finally:
        _enrichment_job["done"] = 1
        _enrichment_job["current_album"] = None
        if _enrichment_job["status"] == "running":
            _enrichment_job["status"] = "done"


async def run_collection_enrichment(session_factory, collection_id: int) -> None:
    """Background task: enrich all albums in a collection sequentially."""
    global _enrichment_job
    from app.models.collection_album import CollectionAlbum
    from app.models.album import Album

    _enrichment_job = {
        "status": "running",
        "total": 0,
        "done": 0,
        "enriched": 0,
        "skipped": 0,
        "errors": 0,
        "error_list": [],
        "cancel_requested": False,
        "current_album": None,
    }

    try:
        async with session_factory() as db:
            rows = (await db.execute(
                select(Album.id, Album.title, Album.artist)
                .join(CollectionAlbum, CollectionAlbum.album_id == Album.id)
                .where(CollectionAlbum.collection_id == collection_id)
                .order_by(Album.title)
            )).all()

        _enrichment_job["total"] = len(rows)

        for album_id, title, artist in rows:
            if _enrichment_job["cancel_requested"]:
                _enrichment_job["status"] = "cancelled"
                return

            await asyncio.sleep(0)
            _enrichment_job["current_album"] = f"{title} — {artist}"

            try:
                async with session_factory() as db:
                    enriched = await enrich_album(db, album_id)
                if enriched:
                    _enrichment_job["enriched"] += 1
                else:
                    _enrichment_job["skipped"] += 1
            except Exception as exc:
                logger.warning("Enrichment failed for album %d (%s): %s", album_id, title, exc)
                _enrichment_job["errors"] += 1
                msg = f"{title} — {exc}"
                if len(_enrichment_job["error_list"]) >= 50:
                    _enrichment_job["error_list"] = _enrichment_job["error_list"][-49:]
                _enrichment_job["error_list"].append(msg)
            finally:
                _enrichment_job["done"] += 1

        _enrichment_job["current_album"] = None
        _enrichment_job["status"] = "done"
        logger.info(
            "Collection enrichment complete: enriched=%d skipped=%d errors=%d",
            _enrichment_job["enriched"], _enrichment_job["skipped"], _enrichment_job["errors"],
        )

    except Exception as exc:
        logger.error("Collection enrichment crashed: %s", exc)
        _enrichment_job["status"] = "error"
        _enrichment_job["error_list"].append(str(exc))


def get_progress() -> dict:
    return dict(_enrichment_job)


def request_cancel() -> None:
    _enrichment_job["cancel_requested"] = True
