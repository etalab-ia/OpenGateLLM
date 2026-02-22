# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

__all__ = ["UserUpdateParams"]


class UserUpdateParams(TypedDict, total=False):
    budget: Optional[float]
    """The new budget. If None, the user will have no budget."""

    current_password: Optional[str]
    """The current user password."""

    email: Optional[str]
    """The new user email. If None, the user email is not changed."""

    expires: Optional[int]
    """The new expiration timestamp. If None, the user will never expire."""

    name: Optional[str]
    """The new user name. If None, the user name is not changed."""

    organization: Optional[int]
    """The new organization ID.

    If None, the user will be removed from the organization if he was in one.
    """

    password: Optional[str]
    """The new user password. If None, the user password is not changed."""

    priority: Optional[int]
    """The new user priority. Higher value means higher priority. If None, unchanged."""

    role: Optional[int]
    """The new role ID. If None, the user role is not changed."""
