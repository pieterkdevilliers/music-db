from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.album import AlbumSummary


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None
    created_at: datetime


class CollectionDetailRead(CollectionRead):
    albums: list[AlbumSummary] = []
