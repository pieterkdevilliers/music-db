from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.album import Album, AlbumDetail, AlbumMusician, AlbumPersonnel
from app.models.detail import Detail
from app.models.musician import Musician
from app.models.person import Person
from app.models.record_label import RecordLabel
from app.schemas.album import AlbumCreate, AlbumDetailInput, AlbumMusicianInput, AlbumPersonnelInput, AlbumUpdate


async def get_or_create_musician(db: AsyncSession, name: str) -> Musician:
    result = await db.execute(select(Musician).where(Musician.name == name))
    musician = result.scalar_one_or_none()
    if musician is None:
        musician = Musician(name=name)
        db.add(musician)
        await db.flush()
    return musician


async def get_or_create_record_label(db: AsyncSession, name: str) -> RecordLabel:
    result = await db.execute(select(RecordLabel).where(RecordLabel.name == name))
    label = result.scalar_one_or_none()
    if label is None:
        label = RecordLabel(name=name)
        db.add(label)
        await db.flush()
    return label


def _album_query():
    return select(Album).options(
        selectinload(Album.record_label),
        selectinload(Album.album_musician_links),
    )


async def _load_album(db: AsyncSession, album_id: int) -> Album | None:
    result = await db.execute(
        select(Album)
        .where(Album.id == album_id)
        .options(
            selectinload(Album.record_label),
            selectinload(Album.album_musician_links),
        )
    )
    album = result.scalar_one_or_none()
    if album is None:
        return None
    # Eagerly load musicians on each link
    for link in album.album_musician_links:
        await db.refresh(link, attribute_names=["musician_id"])
    return album


async def get_album_with_relations(db: AsyncSession, album_id: int) -> Album | None:
    result = await db.execute(
        select(Album)
        .where(Album.id == album_id)
        .options(
            selectinload(Album.record_label),
            selectinload(Album.album_musician_links),
        )
    )
    album = result.scalar_one_or_none()
    if album is None:
        return None
    # Resolve musician objects on each link row
    for link in album.album_musician_links:
        m_result = await db.execute(
            select(Musician).where(Musician.id == link.musician_id)
        )
        link._musician_obj = m_result.scalar_one_or_none()
    return album


async def get_or_create_person(db: AsyncSession, name: str) -> Person:
    result = await db.execute(select(Person).where(Person.name == name))
    person = result.scalar_one_or_none()
    if person is None:
        person = Person(name=name)
        db.add(person)
        await db.flush()
    return person


async def get_or_create_detail(db: AsyncSession, name: str) -> Detail:
    result = await db.execute(select(Detail).where(Detail.name == name))
    detail = result.scalar_one_or_none()
    if detail is None:
        detail = Detail(name=name)
        db.add(detail)
        await db.flush()
    return detail


async def _set_personnel_links(
    db: AsyncSession, album: Album, inputs: list[AlbumPersonnelInput]
) -> None:
    await db.execute(
        delete(AlbumPersonnel).where(AlbumPersonnel.album_id == album.id)
    )
    for inp in inputs:
        person = await get_or_create_person(db, inp.person_name)
        link = AlbumPersonnel(
            album_id=album.id,
            person_id=person.id,
            role=inp.role,
        )
        db.add(link)


async def _set_musician_links(
    db: AsyncSession, album: Album, inputs: list[AlbumMusicianInput]
) -> None:
    await db.execute(
        delete(AlbumMusician).where(AlbumMusician.album_id == album.id)
    )
    for inp in inputs:
        musician = await get_or_create_musician(db, inp.musician_name)
        link = AlbumMusician(
            album_id=album.id,
            musician_id=musician.id,
            instrument=inp.instrument,
        )
        db.add(link)


async def _set_detail_links(
    db: AsyncSession, album: Album, inputs: list[AlbumDetailInput]
) -> None:
    await db.execute(
        delete(AlbumDetail).where(AlbumDetail.album_id == album.id)
    )
    for inp in inputs:
        detail = await get_or_create_detail(db, inp.detail_name)
        link = AlbumDetail(
            album_id=album.id,
            detail_id=detail.id,
            detail_type=inp.detail_type,
        )
        db.add(link)


async def create_album(db: AsyncSession, schema: AlbumCreate) -> Album:
    label_id: int | None = None
    if schema.record_label:
        label = await get_or_create_record_label(db, schema.record_label)
        label_id = label.id

    album = Album(
        title=schema.title,
        artist=schema.artist,
        release_year=schema.release_year,
        producer=schema.producer,
        record_label_id=label_id,
        tracks=schema.tracks,
    )
    db.add(album)
    await db.flush()

    await _set_musician_links(db, album, schema.musicians)
    await _set_personnel_links(db, album, schema.personnel)
    await _set_detail_links(db, album, schema.other_details)
    await db.commit()
    return await get_album_full(db, album.id)  # type: ignore[return-value]


async def update_album(
    db: AsyncSession, album_id: int, schema: AlbumUpdate
) -> Album | None:
    result = await db.execute(select(Album).where(Album.id == album_id))
    album = result.scalar_one_or_none()
    if album is None:
        return None

    if schema.title is not None:
        album.title = schema.title
    if schema.artist is not None:
        album.artist = schema.artist
    if schema.release_year is not None:
        album.release_year = schema.release_year
    if schema.producer is not None:
        album.producer = schema.producer
    if schema.record_label is not None:
        label = await get_or_create_record_label(db, schema.record_label)
        album.record_label_id = label.id
    if schema.tracks is not None:
        album.tracks = schema.tracks
    if schema.musicians is not None:
        await _set_musician_links(db, album, schema.musicians)
    if schema.personnel is not None:
        await _set_personnel_links(db, album, schema.personnel)
    if schema.other_details is not None:
        await _set_detail_links(db, album, schema.other_details)

    await db.commit()
    return await get_album_full(db, album.id)  # type: ignore[return-value]


async def get_album_full(db: AsyncSession, album_id: int) -> Album | None:
    result = await db.execute(
        select(Album)
        .where(Album.id == album_id)
        .options(
            selectinload(Album.record_label),
            selectinload(Album.album_musician_links),
            selectinload(Album.album_personnel_links),
            selectinload(Album.album_detail_links),
        )
    )
    album = result.scalar_one_or_none()
    if album is None:
        return None
    # Resolve musician objects per link
    for link in album.album_musician_links:
        m_result = await db.execute(
            select(Musician).where(Musician.id == link.musician_id)
        )
        link._musician_obj = m_result.scalar_one_or_none()
    # Resolve person objects per personnel link
    for link in album.album_personnel_links:
        p_result = await db.execute(
            select(Person).where(Person.id == link.person_id)
        )
        link._person_obj = p_result.scalar_one_or_none()
    # Resolve detail objects per detail link
    for link in album.album_detail_links:
        d_result = await db.execute(
            select(Detail).where(Detail.id == link.detail_id)
        )
        link._detail_obj = d_result.scalar_one_or_none()
    return album


async def list_albums(
    db: AsyncSession,
    musician_id: int | None = None,
    instrument: str | None = None,
    artist: str | None = None,
    label: str | None = None,
    search: str | None = None,
) -> list[Album]:
    q = select(Album).options(
        selectinload(Album.record_label),
        selectinload(Album.album_musician_links),
        selectinload(Album.album_personnel_links),
        selectinload(Album.album_detail_links),
    )

    if musician_id is not None:
        q = q.join(AlbumMusician, AlbumMusician.album_id == Album.id).where(
            AlbumMusician.musician_id == musician_id
        )
        if instrument is not None:
            q = q.where(AlbumMusician.instrument == instrument)
    elif instrument is not None:
        q = q.join(AlbumMusician, AlbumMusician.album_id == Album.id).where(
            AlbumMusician.instrument == instrument
        )

    if artist is not None:
        q = q.where(Album.artist.ilike(f"%{artist}%"))

    if label is not None:
        q = q.join(RecordLabel, RecordLabel.id == Album.record_label_id).where(
            RecordLabel.name.ilike(f"%{label}%")
        )

    if search is not None:
        q = q.where(
            Album.title.ilike(f"%{search}%") | Album.artist.ilike(f"%{search}%")
        )

    q = q.distinct()
    result = await db.execute(q)
    albums = list(result.scalars().all())

    for album in albums:
        for link in album.album_musician_links:
            m_result = await db.execute(
                select(Musician).where(Musician.id == link.musician_id)
            )
            link._musician_obj = m_result.scalar_one_or_none()
        for link in album.album_personnel_links:
            p_result = await db.execute(
                select(Person).where(Person.id == link.person_id)
            )
            link._person_obj = p_result.scalar_one_or_none()
        for link in album.album_detail_links:
            d_result = await db.execute(
                select(Detail).where(Detail.id == link.detail_id)
            )
            link._detail_obj = d_result.scalar_one_or_none()

    return albums


async def delete_album(db: AsyncSession, album_id: int) -> bool:
    result = await db.execute(select(Album).where(Album.id == album_id))
    album = result.scalar_one_or_none()
    if album is None:
        return False
    await db.delete(album)
    await db.commit()
    return True


async def delete_all_albums(db: AsyncSession) -> int:
    """Delete every album in the database. Returns the count deleted."""
    result = await db.execute(delete(Album))
    await db.commit()
    return result.rowcount
