from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AlbumDetail(Base):
    __tablename__ = "album_details"

    album_id: Mapped[int] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"), primary_key=True
    )
    detail_type: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)


class AlbumPersonnel(Base):
    __tablename__ = "album_personnel"

    album_id: Mapped[int] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)


class AlbumMusician(Base):
    __tablename__ = "album_musicians"

    album_id: Mapped[int] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    musician_id: Mapped[int] = mapped_column(
        ForeignKey("musicians.id", ondelete="CASCADE"), primary_key=True
    )
    instrument: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    producer: Mapped[str | None] = mapped_column(String, nullable=True)
    record_label_id: Mapped[int | None] = mapped_column(
        ForeignKey("record_labels.id", ondelete="SET NULL"), nullable=True
    )
    tracks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    art_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    record_label: Mapped[RecordLabel | None] = relationship()  # noqa: F821
    musicians: Mapped[list[Musician]] = relationship(  # noqa: F821
        secondary="album_musicians", back_populates="albums"
    )
    album_musician_links: Mapped[list[AlbumMusician]] = relationship(
        cascade="all, delete-orphan"
    )
    personnel: Mapped[list[Person]] = relationship(  # noqa: F821
        secondary="album_personnel", back_populates="albums"
    )
    album_personnel_links: Mapped[list[AlbumPersonnel]] = relationship(
        cascade="all, delete-orphan"
    )
    details: Mapped[list[Detail]] = relationship(  # noqa: F821
        secondary="album_details", back_populates="albums"
    )
    album_detail_links: Mapped[list[AlbumDetail]] = relationship(
        cascade="all, delete-orphan"
    )
    collections: Mapped[list[Collection]] = relationship(  # noqa: F821
        secondary="collection_albums", back_populates="albums"
    )
