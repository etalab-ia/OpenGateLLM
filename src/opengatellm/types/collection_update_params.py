# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

from .collection_visibility import CollectionVisibility

__all__ = ["CollectionUpdateParams"]


class CollectionUpdateParams(TypedDict, total=False):
    description: Optional[str]
    """The description of the collection."""

    name: Optional[str]
    """The name of the collection."""

    visibility: Optional[CollectionVisibility]
    """The type of the collection.

    Public collections are available to all users, private collections are only
    available to the user who created them.
    """
