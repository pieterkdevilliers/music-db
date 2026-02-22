from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import AsyncSessionLocal, get_db
from app.models.collection import Collection
from app.models.user import User
from app.services import flac_import as flac_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import/flac", tags=["import"])


class StartImportRequest(BaseModel):
    root_path: str
    collection_id: int | None = None


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_import(
    body: StartImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan root_path for audio files and import all albums.

    root_path must be a path accessible inside the Docker container.
    Mount your music drive as a volume in docker-compose.yml first.
    Runs as a background task — poll GET /import/flac/progress for updates.
    """
    if not body.root_path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="root_path is required.",
        )

    progress = flac_service.get_progress()
    if progress.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Import already in progress.",
        )

    if body.collection_id is not None:
        collection = (await db.execute(
            select(Collection).where(
                Collection.id == body.collection_id,
                Collection.user_id == current_user.id,
            )
        )).scalar_one_or_none()
        if collection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found.",
            )

    root_path = body.root_path.strip()
    flac_service.reset_import_job(root_path=root_path, collection_id=body.collection_id)
    asyncio.create_task(
        flac_service.run_import(
            AsyncSessionLocal,
            root_path=root_path,
            collection_id=body.collection_id,
        )
    )

    return {"status": "starting"}


@router.get("/progress")
async def get_progress(
    _current_user=Depends(get_current_user),
):
    """Return the current file import job progress."""
    return flac_service.get_progress()


@router.post("/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_import(
    _current_user=Depends(get_current_user),
):
    """Request cancellation of the running file import."""
    flac_service.cancel_import()
    return {"status": "cancellation requested"}
