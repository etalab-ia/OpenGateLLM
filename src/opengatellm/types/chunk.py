# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

import builtins
from typing import TYPE_CHECKING, Dict, List, Union, Optional
from typing_extensions import Literal

from pydantic import Field as FieldInfo

from .._models import BaseModel

__all__ = ["Chunk"]


class Chunk(BaseModel):
    id: int
    """The ID of the chunk."""

    collection_id: int
    """The ID of the collection the chunk belongs to."""

    content: str
    """The content of the chunk."""

    document_id: int
    """The ID of the document the chunk belongs to."""

    created: Optional[int] = None
    """The date of the chunk creation."""

    metadata: Optional[Dict[str, Union[str, float, List[Union[str, float, bool, None]], bool, None]]] = None
    """Extra metadata for the source"""

    object: Optional[Literal["chunk"]] = None
    """The type of the object."""

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, builtins.object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> builtins.object: ...
    else:
        __pydantic_extra__: Dict[str, builtins.object]
