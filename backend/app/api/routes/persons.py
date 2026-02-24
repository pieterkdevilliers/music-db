from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.album import AlbumPersonnel
from app.models.person import Person
from app.schemas.person import PersonRead

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonRead])
async def search_persons(
    q: str = Query(default="", description="Name prefix to search"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return persons whose names contain the query string (case-insensitive)."""
    stmt = select(Person).order_by(Person.name)
    if q:
        stmt = stmt.where(Person.name.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{person_id}")
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return a person and all albums they appear on, grouped with their roles."""
    from app.api.routes.albums import _to_album_read
    from app.services.album import get_album_full

    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    links_result = await db.execute(
        select(AlbumPersonnel).where(AlbumPersonnel.person_id == person_id)
    )
    links = list(links_result.scalars().all())

    album_roles: dict[int, list[str]] = {}
    for link in links:
        album_roles.setdefault(link.album_id, []).append(link.role)

    albums_out = []
    for album_id, roles in album_roles.items():
        album = await get_album_full(db, album_id)
        if album:
            albums_out.append({"album": _to_album_read(album), "roles": roles})

    return {
        "person": PersonRead.model_validate(person),
        "albums": albums_out,
    }
