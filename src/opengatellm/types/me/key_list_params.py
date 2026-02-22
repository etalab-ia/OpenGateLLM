# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal, TypedDict

__all__ = ["KeyListParams"]


class KeyListParams(TypedDict, total=False):
    limit: int
    """The limit of the tokens to get."""

    offset: int
    """The offset of the tokens to get."""

    order_by: Literal["id", "name", "created"]
    """The field to order the tokens by."""

    order_direction: Literal["asc", "desc"]
    """The direction to order the tokens by."""
