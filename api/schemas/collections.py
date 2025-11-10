from enum import Enum
from typing import Annotated, Literal

from pydantic import StringConstraints

from api.schemas import BaseModel


class CollectionVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


CollectionName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Collection(BaseModel):
    object: Literal["collection"] = "collection"
    id: int
    name: str
    owner: str
    description: str | None = None
    visibility: CollectionVisibility | None = None
    created_at: int
    updated_at: int
    documents: int = 0


class Collections(BaseModel):
    object: Literal["list"] = "list"
    data: list[Collection]
