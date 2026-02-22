# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal, TypedDict

__all__ = ["OrganizationListParams"]


class OrganizationListParams(TypedDict, total=False):
    limit: int
    """The limit of the organizations to get."""

    offset: int
    """The offset of the organizations to get."""

    order_by: Literal["id", "name", "created", "updated"]
    """The field to order the organizations by."""

    order_direction: Literal["asc", "desc"]
    """The direction to order the organizations by."""
