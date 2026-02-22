# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Iterable, Optional
from typing_extensions import Required, TypeAlias, TypedDict

from ..._types import SequenceNotStr

__all__ = ["ChunkCreateParams", "Chunk"]


class ChunkCreateParams(TypedDict, total=False):
    chunks: Required[Iterable[Chunk]]
    """The list of chunks to create."""


class ChunkTyped(TypedDict, total=False):
    content: Required[str]
    """The content of the chunk."""

    metadata: Optional[Dict[str, Union[str, float, SequenceNotStr[Union[str, float, bool, None]], bool, None]]]
    """Extra metadata for the source"""


Chunk: TypeAlias = Union[ChunkTyped, Dict[str, object]]
