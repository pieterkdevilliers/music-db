from pydantic import BaseModel, ConfigDict


class MusicianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AlbumMusicianEntry(BaseModel):
    musician: MusicianRead
    instrument: str
