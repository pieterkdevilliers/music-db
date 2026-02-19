from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumRead, AlbumUpdate
from app.schemas.musician import AlbumMusicianEntry, MusicianRead
from app.services import album as album_service

router = APIRouter(prefix="/albums", tags=["albums"])


def _to_album_read(album) -> AlbumRead:
    musicians = [
        AlbumMusicianEntry(
            musician=MusicianRead.model_validate(link._musician_obj),
            instrument=link.instrument,
        )
        for link in album.album_musician_links
        if link._musician_obj is not None
    ]
    return AlbumRead(
        id=album.id,
        title=album.title,
        artist=album.artist,
        release_year=album.release_year,
        producer=album.producer,
        record_label=album.record_label.name if album.record_label else None,
        tracks=album.tracks or [],
        musicians=musicians,
        created_at=album.created_at,
    )


@router.get("", response_model=list[AlbumRead])
async def list_albums(
    musician_id: int | None = Query(default=None),
    instrument: str | None = Query(default=None),
    artist: str | None = Query(default=None),
    label: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    albums = await album_service.list_albums(
        db,
        musician_id=musician_id,
        instrument=instrument,
        artist=artist,
        label=label,
        search=search,
    )
    return [_to_album_read(a) for a in albums]


@router.post("", response_model=AlbumRead, status_code=status.HTTP_201_CREATED)
async def create_album(
    schema: AlbumCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = await album_service.create_album(db, schema)
    return _to_album_read(album)


@router.get("/{album_id}", response_model=AlbumRead)
async def get_album(
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = await album_service.get_album_full(db, album_id)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_album_read(album)


@router.patch("/{album_id}", response_model=AlbumRead)
async def update_album(
    album_id: int,
    schema: AlbumUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    album = await album_service.update_album(db, album_id, schema)
    if album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_album_read(album)


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await album_service.delete_album(db, album_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
