# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Required, TypedDict

from .collection_visibility import CollectionVisibility

__all__ = ["CollectionCreateParams"]


class CollectionCreateParams(TypedDict, total=False):
    name: Required[str]
    """The name of the collection."""

    description: Optional[str]
    """The description of the collection."""

    visibility: CollectionVisibility
    """The type of the collection.

    Public collections are available to all users, private collections are only
    available to the user who created them.
    """
