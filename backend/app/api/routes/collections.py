from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.album import AlbumSummary
from app.schemas.collection import (
    CollectionCreate,
    CollectionDetailRead,
    CollectionRead,
    CollectionUpdate,
)
from app.services import collection as collection_service

router = APIRouter(prefix="/collections", tags=["collections"])


def _to_detail(collection) -> CollectionDetailRead:
    albums = [
        AlbumSummary(
            id=a.id,
            title=a.title,
            artist=a.artist,
            release_year=a.release_year,
            record_label=a.record_label.name if a.record_label else None,
            art_path=a.art_path,
        )
        for a in collection.albums
    ]
    return CollectionDetailRead(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        created_at=collection.created_at,
        albums=albums,
    )


@router.get("", response_model=list[CollectionDetailRead])
async def list_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collections = await collection_service.list_collections(db, current_user.id)
    return [_to_detail(c) for c in collections]


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    schema: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await collection_service.create_collection(db, current_user.id, schema)


@router.get("/{collection_id}", response_model=CollectionDetailRead)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = await collection_service.get_collection(
        db, collection_id, current_user.id
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_detail(collection)


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: int,
    schema: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = await collection_service.update_collection(
        db, collection_id, current_user.id, schema
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await collection_service.delete_collection(
        db, collection_id, current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.delete("/{collection_id}/albums", status_code=status.HTTP_200_OK)
async def delete_all_albums_in_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete all albums that belong to this collection."""
    count = await collection_service.delete_albums_in_collection(
        db, collection_id, current_user.id
    )
    if count == -1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": count}


@router.post(
    "/{collection_id}/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def add_album(
    collection_id: int,
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await collection_service.add_album_to_collection(
        db, collection_id, album_id, current_user.id
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection or album not found",
        )


@router.delete(
    "/{collection_id}/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_album(
    collection_id: int,
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await collection_service.remove_album_from_collection(
        db, collection_id, album_id, current_user.id
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
