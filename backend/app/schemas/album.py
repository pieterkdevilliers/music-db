from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.musician import AlbumMusicianEntry


class AlbumSummary(BaseModel):
    id: int
    title: str
    artist: str
    release_year: int | None
    record_label: str | None


class AlbumMusicianInput(BaseModel):
    musician_name: str
    instrument: str


class AlbumCreate(BaseModel):
    title: str
    artist: str
    release_year: int | None = None
    producer: str | None = None
    record_label: str | None = None
    tracks: list[str] = []
    musicians: list[AlbumMusicianInput] = []


class AlbumUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    release_year: int | None = None
    producer: str | None = None
    record_label: str | None = None
    tracks: list[str] | None = None
    musicians: list[AlbumMusicianInput] | None = None


class AlbumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: str
    release_year: int | None
    producer: str | None
    record_label: str | None
    tracks: list[str]
    musicians: list[AlbumMusicianEntry]
    created_at: datetime
