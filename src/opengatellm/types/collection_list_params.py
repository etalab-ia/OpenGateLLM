# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

from .collection_visibility import CollectionVisibility

__all__ = ["CollectionListParams"]


class CollectionListParams(TypedDict, total=False):
    limit: int
    """The limit of the collections to get."""

    name: str
    """Filter by collection name."""

    offset: int
    """The offset of the collections to get."""

    visibility: Optional[CollectionVisibility]
    """Filter by collection visibility."""
