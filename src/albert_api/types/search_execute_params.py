# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Optional
from typing_extensions import Literal, Required, TypedDict

__all__ = ["SearchExecuteParams"]


class SearchExecuteParams(TypedDict, total=False):
    collections: Required[List[Union[str, Literal["internet"]]]]

    k: Required[int]
    """Number of results to return"""

    prompt: Required[str]

    score_threshold: Optional[float]
    """Score of cosine similarity threshold for filtering results"""
