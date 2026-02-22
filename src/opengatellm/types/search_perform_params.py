# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Iterable
from typing_extensions import Required, TypedDict

from .search_method import SearchMethod

__all__ = ["SearchPerformParams"]


class SearchPerformParams(TypedDict, total=False):
    collections: Required[Iterable[int]]
    """List of collections ID"""

    prompt: Required[str]
    """Prompt related to the search"""

    limit: int
    """Number of results to return"""

    method: SearchMethod
    """Search method to use"""

    offset: int
    """Offset for pagination, specifying how many results to skip from the beginning"""

    rff_k: int
    """
    Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search
    (recommended: from 10 to 100).
    """

    score_threshold: float
    """
    Score of cosine similarity threshold for filtering results, only available for
    semantic search method.
    """
