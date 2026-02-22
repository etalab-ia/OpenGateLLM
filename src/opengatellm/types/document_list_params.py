# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

__all__ = ["DocumentListParams"]


class DocumentListParams(TypedDict, total=False):
    collection_id: Optional[int]
    """Filter documents by collection ID"""

    limit: int
    """The number of documents to return"""

    name: Optional[str]
    """Filter documents by name"""

    offset: int
    """The offset of the first document to return"""
