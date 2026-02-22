# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import TYPE_CHECKING, List, Optional
from typing_extensions import Literal

from .._models import BaseModel

__all__ = ["Chunks", "Data", "DataMetadata"]


class DataMetadata(BaseModel):
    collection_id: str

    document_id: str

    document_name: str

    document_part: int

    if TYPE_CHECKING:
        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...


class Data(BaseModel):
    id: str

    content: str

    metadata: DataMetadata

    object: Optional[Literal["chunk"]] = None


class Chunks(BaseModel):
    data: List[Data]

    object: Optional[Literal["list"]] = None
