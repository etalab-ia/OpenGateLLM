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

    @classmethod
    def from_elasticsearch(cls, hit: dict) -> "ChunkMetadata":
        return cls(
            collection_id=hit["_source"]["collection_id"],
            document_id=hit["_source"]["document_id"],
            document_name=hit["_source"]["document_name"],
            created=hit["_source"]["created"],
            source_ref=hit["_source"]["source_ref"],
            source_url=hit["_source"]["source_url"],
            source_type=hit["_source"]["source_type"],
            source_page=hit["_source"]["source_page"],
            source_format=hit["_source"]["source_format"],
            source_title=hit["_source"]["source_title"],
            source_author=hit["_source"]["source_author"],
            source_publisher=hit["_source"]["source_publisher"],
            source_priority=hit["_source"]["source_priority"],
            source_tags=hit["_source"]["source_tags"],
            source_date=hit["_source"]["source_date"],
        )


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int
    metadata: ChunkMetadata | None = None
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: list[Chunk]
