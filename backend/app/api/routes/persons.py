from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
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
