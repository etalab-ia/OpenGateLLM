from enum import Enum
from typing import Literal

from pydantic import Field, constr

from api.schemas import BaseModel


class CollectionVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class CollectionRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(description="The name of the collection.")
    description: str | None = Field(default=None, description="The description of the collection.")
    visibility: CollectionVisibility = Field(default=CollectionVisibility.PRIVATE, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off


class CollectionUpdateRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="The name of the collection.")
    description: str | None = Field(default=None, description="The description of the collection.")
    visibility: CollectionVisibility | None = Field(default=None, description="The type of the collection. Public collections are available to all users, private collections are only available to the user who created them.")  # fmt: off


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
