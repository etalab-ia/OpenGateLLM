# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, TypedDict

__all__ = ["TokenListParams"]


class TokenListParams(TypedDict, total=False):
    limit: int
    """The limit of the tokens to get."""

    offset: int
    """The offset of the tokens to get."""

    order_by: Literal["id", "name", "created"]
    """The field to order the tokens by."""

    order_direction: Literal["asc", "desc"]
    """The direction to order the tokens by."""

    user: Optional[int]
    """The user ID of the user to get the tokens for."""
