from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.album import Album
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumRead, AlbumUpdate
from app.schemas.detail import AlbumDetailEntry, DetailRead
from app.schemas.musician import AlbumMusicianEntry, MusicianRead
from app.schemas.person import AlbumPersonnelEntry, PersonRead
from app.services import album as album_service
from app.services.musicbrainz import ALBUM_ART_DIR, download_cover_art

router = APIRouter(prefix="/albums", tags=["albums"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_ART_BYTES = 5 * 1024 * 1024  # 5 MB


def _to_album_read(album) -> AlbumRead:
    musicians = [
        AlbumMusicianEntry(
            musician=MusicianRead.model_validate(link._musician_obj),
            instrument=link.instrument,
        )
        for link in album.album_musician_links
        if link._musician_obj is not None
    ]
    personnel = [
        AlbumPersonnelEntry(
            person=PersonRead.model_validate(link._person_obj),
            role=link.role,
        )
        for link in album.album_personnel_links
        if link._person_obj is not None
    ]
    other_details = [
        AlbumDetailEntry(
            detail=DetailRead.model_validate(link._detail_obj),
            detail_type=link.detail_type,
        )
        for link in album.album_detail_links
        if link._detail_obj is not None
    ]
    return AlbumRead(
        id=album.id,
        title=album.title,
        artist=album.artist,
        release_year=album.release_year,
        producer=album.producer,
        record_label=album.record_label.name if album.record_label else None,
        art_path=album.art_path,
        tracks=album.tracks or [],
        musicians=musicians,
        personnel=personnel,
        other_details=other_details,
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

    if schema.mbid:
        ext = "jpg"
        dest = ALBUM_ART_DIR / f"{album.id}.{ext}"
        downloaded = await download_cover_art(schema.mbid, dest)
        if downloaded:
            result = await db.execute(select(Album).where(Album.id == album.id))
            db_album = result.scalar_one()
            db_album.art_path = f"{album.id}.{ext}"
            await db.commit()
            album = await album_service.get_album_full(db, album.id)  # type: ignore[assignment]

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


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_albums(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Permanently delete every album in the database."""
    count = await album_service.delete_all_albums(db)
    return {"deleted": count}


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await album_service.delete_album(db, album_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/{album_id}/art", response_model=AlbumRead)
async def upload_art(
    album_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a cover art image for an album manually."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_ART_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image too large. Maximum size is 5 MB.",
        )

    result = await db.execute(select(Album).where(Album.id == album_id))
    db_album = result.scalar_one_or_none()
    if db_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    ext = (file.content_type or "image/jpeg").split("/")[-1].replace("jpeg", "jpg")
    filename = f"{album_id}.{ext}"
    dest = ALBUM_ART_DIR / filename
    dest.write_bytes(content)

    # Remove old file with a different extension if it exists
    if db_album.art_path and db_album.art_path != filename:
        old = ALBUM_ART_DIR / db_album.art_path
        old.unlink(missing_ok=True)

    db_album.art_path = filename
    await db.commit()

    album = await album_service.get_album_full(db, album_id)
    return _to_album_read(album)  # type: ignore[arg-type]


@router.delete("/{album_id}/art", response_model=AlbumRead)
async def delete_art(
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove the cover art for an album."""
    result = await db.execute(select(Album).where(Album.id == album_id))
    db_album = result.scalar_one_or_none()
    if db_album is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if db_album.art_path:
        (ALBUM_ART_DIR / db_album.art_path).unlink(missing_ok=True)
        db_album.art_path = None
        await db.commit()

    album = await album_service.get_album_full(db, album_id)
    return _to_album_read(album)  # type: ignore[arg-type]
