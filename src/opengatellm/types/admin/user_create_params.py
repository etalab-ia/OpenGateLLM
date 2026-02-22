# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Required, TypedDict

__all__ = ["UserCreateParams"]


class UserCreateParams(TypedDict, total=False):
    email: Required[str]
    """The user email."""

    password: Required[str]
    """The user password."""

    role: Required[int]
    """The role ID."""

    budget: Optional[float]
    """The budget."""

    expires: Optional[int]
    """The expiration timestamp."""

    name: Optional[str]
    """The user name."""

    organization: Optional[int]
    """The organization ID."""

    priority: Optional[int]
    """The user priority. Higher value means higher priority. 0 is default."""
