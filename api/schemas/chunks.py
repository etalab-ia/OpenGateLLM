from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_serializer, model_validator

from api.schemas import BaseModel

MIN_NUMBER, MAX_NUMBER = -9999999999999999, 9999999999999999

MetadataStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
MetadataInt = Annotated[int, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataFloat = Annotated[float, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataList = Annotated[list[MetadataStr | MetadataInt | MetadataFloat | bool | None], Field(max_length=8)]

ChunkMetadata = Annotated[dict[MetadataStr, MetadataStr | MetadataInt | MetadataFloat | MetadataList | bool | None], Field(description="Extra metadata for the source", min_length=1, max_length=8)]  # fmt: off


class InputChunk(BaseModel):
    content: Annotated[str, Field(default=..., description="The content of the chunk.")]
    metadata: Annotated[ChunkMetadata | None, Field(default=None, description="Metadata of the chunk")]


class CreateChunks(BaseModel):
    chunks: Annotated[list[InputChunk], Field(min_length=1, max_length=64, description="The list of chunks to create.")]

    @model_validator(mode="after")
    def validate_total_content_size(self):
        if sum(len(chunk.content) for chunk in self.chunks) > 1024 * 1024 * 20:  # 20MB
            raise ValueError("Chunks content total size exceeds 20MB")  # TODO setup value in config

        return self


class ChunksResponse(BaseModel):
    document_id: Annotated[int, Field(ge=0, default=..., description="The ID of the document the chunks belong to.")]
    ids: Annotated[list[int], Field(min_length=1, description="The list of IDs of the created chunks.")]


class Chunk(BaseModel):
    object: Annotated[Literal["chunk"], Field(default="chunk", description="The type of the object.")]
    id: Annotated[int, Field(ge=0, default=..., description="The ID of the chunk.")]
    collection_id: Annotated[int, Field(ge=0, default=..., description="The ID of the collection the chunk belongs to.")]
    document_id: Annotated[int, Field(ge=0, default=..., description="The ID of the document the chunk belongs to.")]
    content: Annotated[str, Field(min_length=1, default=..., description="The content of the chunk.")]
    metadata: Annotated[ChunkMetadata | None, Field(default=None, description="Metadata of the chunk")]
    created: Annotated[datetime, Field(default=datetime.now(), description="The date of the chunk creation.")]

    @field_serializer("created")
    def serialize_created(self, created: datetime) -> int:
        return int(created.timestamp())


class Chunks(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="The type of the object.")]
    data: Annotated[list[Chunk], Field(description="The list of chunks.")]
