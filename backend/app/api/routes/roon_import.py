from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import AsyncSessionLocal, get_db
from app.models.collection import Collection
from app.models.user import User
from app.services import roon as roon_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import/roon", tags=["import"])


class ConnectRequest(BaseModel):
    host: str = ""
    port: int = 9330


class StartImportRequest(BaseModel):
    collection_id: int | None = None
    auto_enrich: bool = False


@router.post("/connect", status_code=status.HTTP_202_ACCEPTED)
async def connect(
    body: ConnectRequest,
    _current_user=Depends(get_current_user),
):
    """Initiate a connection to the Roon Core (non-blocking).

    After calling this endpoint, the user must open Roon > Settings > Extensions
    and click Enable next to "Music DB Importer".  Poll GET /import/roon/status
    until authorized is true.
    """
    host = body.host or settings.roon_host
    port = body.port or settings.roon_port

    if not host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roon Core host is required. Set ROON_HOST env var or pass host in the request body.",
        )

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: roon_service.connect(host, port))
    except Exception as exc:
        logger.warning("Roon connect failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not connect to Roon Core at {host}:{port} — {exc}",
        ) from exc

    return {"status": "connecting", "host": host, "port": port}


@router.get("/status")
async def get_status(
    _current_user=Depends(get_current_user),
):
    """Return the current Roon connection and authorization status."""
    return roon_service.get_status()


@router.get("/probe")
async def probe(
    count: int = 3,
    _current_user=Depends(get_current_user),
):
    """Fetch raw Roon data for the first `count` albums (max 10).

    Returns unprocessed Roon browse API output so you can review the available
    fields before designing the full import mapping.
    """
    count = min(count, 10)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: roon_service.probe(count))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.warning("Roon probe failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Roon probe failed: {exc}",
        ) from exc

    return result


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_import(
    body: StartImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a bulk import of all albums from the connected Roon library.

    Optionally supply collection_id to add every imported/updated album to
    that collection.  Runs as a background task — poll GET /import/roon/progress
    for updates.
    """
    status_info = roon_service.get_status()
    if not status_info.get("authorized"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Roon Core not authorized. Connect and authorize first.",
        )

    progress = roon_service.get_progress()
    if progress.get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Import already in progress.",
        )

    # Validate the collection belongs to the current user
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

    roon_service.reset_import_job(collection_id=body.collection_id)
    asyncio.create_task(
        roon_service.run_import(
            AsyncSessionLocal,
            collection_id=body.collection_id,
            auto_enrich=body.auto_enrich,
        )
    )

    return {"status": "starting"}


@router.get("/progress")
async def get_progress(
    _current_user=Depends(get_current_user),
):
    """Return the current import job progress."""
    return roon_service.get_progress()


@router.post("/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_import(
    _current_user=Depends(get_current_user),
):
    """Request cancellation of the running import."""
    roon_service.cancel_import()
    return {"status": "cancellation requested"}
