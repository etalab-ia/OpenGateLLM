from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_serializer

from api.schemas import BaseModel

MIN_NUMBER, MAX_NUMBER = -9999999999999999, 9999999999999999

MetadataStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
MetadataInt = Annotated[int, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataFloat = Annotated[float, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataList = Annotated[list[MetadataStr | MetadataInt | MetadataFloat | bool | None], Field(max_length=8)]

ChunkMetadata = Annotated[dict[MetadataStr, MetadataStr | MetadataInt | MetadataFloat | MetadataList | bool | None], Field(description="Extra metadata for the source", min_length=1, max_length=8)]  # fmt: off


class Chunk(BaseModel):
    object: Annotated[Literal["chunk"], Field(default="chunk", description="The type of the object.")]
    id: Annotated[int, Field(ge=0, default=..., description="The ID of the chunk.")]
    collection: Annotated[int, Field(ge=0, default=..., description="The ID of the collection the chunk belongs to.")]
    document: Annotated[int, Field(ge=0, default=..., description="The ID of the document the chunk belongs to.")]
    document_name: Annotated[str, Field(min_length=1, max_length=255, default=..., description="The name of the document the chunk belongs to.")]
    content: Annotated[str, Field(min_length=1, default=..., description="The content of the chunk.")]
    metadata: ChunkMetadata | None = Field(default=None, description="Metadata of the chunk")
    created: Annotated[datetime, Field(default=datetime.now(), description="The date of the chunk creation.")]

    @field_serializer("created")
    def serialize_created(self, created: datetime) -> int:
        return int(created.timestamp())

    @classmethod
    def from_elasticsearch(cls, hit: dict) -> "Chunk":
        return cls(
            id=hit["_source"]["id"],
            collection=hit["_source"]["collection_id"],
            document=hit["_source"]["document_id"],
            document_name=hit["_source"]["document_name"],
            content=hit["_source"]["content"],
            metadata=hit["_source"]["metadata"],
            created=hit["_source"]["created"],
        )


class Chunks(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Chunk], Field(description="The list of chunks.")]
