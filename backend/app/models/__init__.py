from app.models.user import User
from app.models.record_label import RecordLabel
from app.models.musician import Musician
from app.models.person import Person
from app.models.detail import Detail
from app.models.album import Album, AlbumDetail, AlbumMusician, AlbumPersonnel
from app.models.collection import Collection
from app.models.collection_album import CollectionAlbum

__all__ = [
    "User",
    "RecordLabel",
    "Musician",
    "Person",
    "Detail",
    "Album",
    "AlbumDetail",
    "AlbumMusician",
    "AlbumPersonnel",
    "Collection",
    "CollectionAlbum",
]
