from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import Album
from app.models.collection import Collection
from app.models.collection_album import CollectionAlbum
from app.schemas.collection import CollectionCreate, CollectionUpdate


async def create_collection(
    db: AsyncSession, user_id: int, schema: CollectionCreate
) -> Collection:
    collection = Collection(
        user_id=user_id,
        name=schema.name,
        description=schema.description,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection


async def list_collections(db: AsyncSession, user_id: int) -> list[Collection]:
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == user_id)
        .options(
            selectinload(Collection.albums).selectinload(Album.record_label)
        )
    )
    return list(result.scalars().all())


async def get_collection(
    db: AsyncSession, collection_id: int, user_id: int
) -> Collection | None:
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == user_id)
        .options(
            selectinload(Collection.albums).selectinload(Album.record_label)
        )
    )
    return result.scalar_one_or_none()


async def update_collection(
    db: AsyncSession, collection_id: int, user_id: int, schema: CollectionUpdate
) -> Collection | None:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        return None
    if schema.name is not None:
        collection.name = schema.name
    if schema.description is not None:
        collection.description = schema.description
    await db.commit()
    await db.refresh(collection)
    return collection


async def delete_collection(
    db: AsyncSession, collection_id: int, user_id: int
) -> bool:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        return False
    await db.delete(collection)
    await db.commit()
    return True


async def add_album_to_collection(
    db: AsyncSession, collection_id: int, album_id: int, user_id: int
) -> bool:
    collection = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    if collection.scalar_one_or_none() is None:
        return False

    album_exists = await db.execute(select(Album).where(Album.id == album_id))
    if album_exists.scalar_one_or_none() is None:
        return False

    existing = await db.execute(
        select(CollectionAlbum).where(
            CollectionAlbum.collection_id == collection_id,
            CollectionAlbum.album_id == album_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return True  # Already present

    link = CollectionAlbum(collection_id=collection_id, album_id=album_id)
    db.add(link)
    await db.commit()
    return True


async def remove_album_from_collection(
    db: AsyncSession, collection_id: int, album_id: int, user_id: int
) -> bool:
    collection = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    if collection.scalar_one_or_none() is None:
        return False

    result = await db.execute(
        select(CollectionAlbum).where(
            CollectionAlbum.collection_id == collection_id,
            CollectionAlbum.album_id == album_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        return False
    await db.delete(link)
    await db.commit()
    return True
