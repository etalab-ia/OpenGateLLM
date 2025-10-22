from typing import Any, Literal

from api.schemas import BaseModel


class Chunk(BaseModel):
    object: Literal["chunk"] = "chunk"
    id: int
    metadata: dict[str, Any]
    content: str


class Chunks(BaseModel):
    object: Literal["list"] = "list"
    data: list[Chunk]
