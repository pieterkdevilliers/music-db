from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import AsyncSessionLocal, get_db
from app.models.collection import Collection
from app.models.user import User
from app.services import enrichment as enrichment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/album/{album_id}", status_code=status.HTTP_202_ACCEPTED)
async def enrich_album(
    album_id: int,
    _current_user: User = Depends(get_current_user),
):
    """Start AI enrichment for a single album.

    Runs as a background task. Poll GET /enrichment/progress for status.
    """
    progress = enrichment_service.get_progress()
    if progress.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enrichment already in progress.",
        )

    asyncio.create_task(
        enrichment_service.run_album_enrichment(AsyncSessionLocal, album_id)
    )
    return {"status": "starting"}


@router.post("/collection/{collection_id}", status_code=status.HTTP_202_ACCEPTED)
async def enrich_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start AI enrichment for all albums in a collection.

    Runs as a background task. Poll GET /enrichment/progress for status.
    """
    progress = enrichment_service.get_progress()
    if progress.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enrichment already in progress.",
        )

    collection = (await db.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")

    asyncio.create_task(
        enrichment_service.run_collection_enrichment(AsyncSessionLocal, collection_id)
    )
    return {"status": "starting"}


@router.get("/progress")
async def get_progress(
    _current_user: User = Depends(get_current_user),
):
    """Return the current enrichment job progress."""
    return enrichment_service.get_progress()


@router.post("/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_enrichment(
    _current_user: User = Depends(get_current_user),
):
    """Request cancellation of the running enrichment job."""
    enrichment_service.request_cancel()
    return {"status": "cancellation requested"}
