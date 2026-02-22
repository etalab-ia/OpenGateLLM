# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import TypedDict

__all__ = ["ChunkListParams"]


class ChunkListParams(TypedDict, total=False):
    limit: int
    """The number of documents to return"""

    offset: int
    """The offset of the first document to return"""
