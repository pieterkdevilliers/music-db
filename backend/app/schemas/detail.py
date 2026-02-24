from pydantic import BaseModel, ConfigDict


class DetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AlbumDetailEntry(BaseModel):
    detail: DetailRead
    detail_type: str
