from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.services.musicbrainz import get_release, search_releases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/musicbrainz", tags=["musicbrainz"])


@router.get("/search")
async def search(
    title: str = Query(..., min_length=1),
    artist: str = Query(..., min_length=1),
    _current_user=Depends(get_current_user),
) -> list[dict]:
    """Search MusicBrainz for releases matching title + artist.

    Returns up to 10 candidate releases for the user to confirm.
    """
    try:
        return await search_releases(title, artist)
    except httpx.HTTPError as e:
        logger.warning("MusicBrainz search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="MusicBrainz is currently unavailable",
        ) from e


@router.get("/release/{mbid}")
async def fetch_release(
    mbid: str,
    _current_user=Depends(get_current_user),
) -> dict:
    """Fetch full release details from MusicBrainz by MBID.

    Returns title, artist, year, label, and track list for form pre-population.
    """
    try:
        return await get_release(mbid)
    except httpx.HTTPError as e:
        logger.warning("MusicBrainz release fetch failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="MusicBrainz is currently unavailable",
        ) from e
