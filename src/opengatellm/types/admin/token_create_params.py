# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Required, TypedDict

__all__ = ["TokenCreateParams"]


class TokenCreateParams(TypedDict, total=False):
    name: Required[str]

    user: Required[int]
    """User ID to create the token for another user (by default, the current user).

    Required CREATE_USER permission.
    """

    expires: Optional[int]
    """Timestamp in seconds"""
