# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal, TypedDict

__all__ = ["RoleListParams"]


class RoleListParams(TypedDict, total=False):
    limit: int
    """The limit of the roles to get."""

    offset: int
    """The offset of the roles to get."""

    order_by: Literal["id", "name", "created", "updated"]
    """The field to order the roles by."""

    order_direction: Literal["asc", "desc"]
    """The direction to order the roles by."""
