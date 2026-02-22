# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, TypedDict

__all__ = ["MeGetUsageParams"]


class MeGetUsageParams(TypedDict, total=False):
    end_time: Optional[int]
    """End time as Unix timestamp (if not provided, will be set to now)"""

    endpoint: Optional[
        Literal[
            "/v1/audio/transcriptions", "/v1/chat/completions", "/v1/embeddings", "/v1/ocr", "/v1/rerank", "/v1/search"
        ]
    ]
    """The endpoint to get usage for."""

    limit: int
    """The limit of the usages to get."""

    offset: int
    """The offset of the usages to get."""

    start_time: Optional[int]
    """Start time as Unix timestamp (if not provided, will be set to 30 days ago)"""
