from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.album import AlbumDetail
from app.models.detail import Detail
from app.schemas.detail import DetailRead

router = APIRouter(prefix="/details", tags=["details"])


@router.get("", response_model=list[DetailRead])
async def search_details(
    q: str = Query(default="", description="Name prefix to search"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return details whose names contain the query string (case-insensitive)."""
    stmt = select(Detail).order_by(Detail.name)
    if q:
        stmt = stmt.where(Detail.name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{detail_id}")
async def get_detail(
    detail_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return a detail and all albums that reference it, with detail_type per album."""
    from app.api.routes.albums import _to_album_read
    from app.services.album import get_album_full

    result = await db.execute(select(Detail).where(Detail.id == detail_id))
    detail = result.scalar_one_or_none()
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    links_result = await db.execute(
        select(AlbumDetail).where(AlbumDetail.detail_id == detail_id)
    )
    links = list(links_result.scalars().all())

    # A detail can appear on the same album with multiple types (rare but possible)
    album_types: dict[int, list[str]] = {}
    for link in links:
        album_types.setdefault(link.album_id, []).append(link.detail_type)

    albums_out = []
    for album_id, types in album_types.items():
        album = await get_album_full(db, album_id)
        if album:
            albums_out.append({"album": _to_album_read(album), "types": types})

    return {
        "detail": DetailRead.model_validate(detail),
        "albums": albums_out,
    }
