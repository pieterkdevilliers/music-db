from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.musician import AlbumMusicianEntry
from app.schemas.person import AlbumPersonnelEntry


class AlbumSummary(BaseModel):
    id: int
    title: str
    artist: str
    release_year: int | None
    record_label: str | None
    art_path: str | None


class AlbumMusicianInput(BaseModel):
    musician_name: str
    instrument: str


class AlbumPersonnelInput(BaseModel):
    person_name: str
    role: str


class AlbumCreate(BaseModel):
    title: str
    artist: str
    release_year: int | None = None
    producer: str | None = None
    record_label: str | None = None
    tracks: list[str] = []
    musicians: list[AlbumMusicianInput] = []
    personnel: list[AlbumPersonnelInput] = []
    mbid: str | None = None  # MusicBrainz release ID; triggers art download if set


class AlbumUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    release_year: int | None = None
    producer: str | None = None
    record_label: str | None = None
    tracks: list[str] | None = None
    musicians: list[AlbumMusicianInput] | None = None
    personnel: list[AlbumPersonnelInput] | None = None


class AlbumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: str
    release_year: int | None
    producer: str | None
    record_label: str | None
    art_path: str | None
    tracks: list[str]
    musicians: list[AlbumMusicianEntry]
    personnel: list[AlbumPersonnelEntry]
    created_at: datetime
