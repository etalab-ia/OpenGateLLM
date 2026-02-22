# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, TypedDict

__all__ = ["UserListParams"]


class UserListParams(TypedDict, total=False):
    email: Optional[str]
    """The email of the user to filter the users by."""

    limit: int
    """The limit of the users to get."""

    offset: int
    """The offset of the users to get."""

    order_by: Literal["id", "name", "created", "updated"]
    """The field to order the users by."""

    order_direction: Literal["asc", "desc"]
    """The direction to order the users by."""

    organization: Optional[int]
    """The ID of the organization to filter the users by."""

    role: Optional[int]
    """The ID of the role to filter the users by."""
