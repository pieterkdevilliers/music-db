from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.album import Album, AlbumMusician
from app.models.musician import Musician
from app.schemas.album import AlbumRead
from app.schemas.musician import AlbumMusicianEntry, MusicianRead

router = APIRouter(prefix="/musicians", tags=["musicians"])


@router.get("", response_model=list[MusicianRead])
async def list_musicians(
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(Musician).order_by(Musician.name)
    if search:
        q = q.where(Musician.name.ilike(f"%{search}%"))
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{musician_id}")
async def get_musician(
    musician_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Musician).where(Musician.id == musician_id))
    musician = result.scalar_one_or_none()
    if musician is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Load albums for this musician along with their musician links
    links_result = await db.execute(
        select(AlbumMusician)
        .where(AlbumMusician.musician_id == musician_id)
    )
    links = list(links_result.scalars().all())

    # Load each album's full data
    from app.services.album import get_album_full
    from app.api.routes.albums import _to_album_read

    album_ids_instruments: dict[int, list[str]] = {}
    for link in links:
        album_ids_instruments.setdefault(link.album_id, []).append(link.instrument)

    albums_out = []
    for album_id, instruments in album_ids_instruments.items():
        album = await get_album_full(db, album_id)
        if album:
            albums_out.append(
                {
                    "album": _to_album_read(album),
                    "instruments": instruments,
                }
            )

    return {
        "musician": MusicianRead.model_validate(musician),
        "albums": albums_out,
    }
