from datetime import datetime
from typing import Literal

from pydantic import field_serializer

from api.schemas import BaseModel
from api.schemas.documents import InputChunkMetadata


class ChunkMetadata(InputChunkMetadata):
    collection_id: int
    document_id: int
    document_name: str
    created: datetime

    @field_serializer("created")
    def serialize_created(self, created: datetime) -> int:
        return int(created.timestamp())


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int
    metadata: ChunkMetadata | None = None
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: list[Chunk]
