# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

__all__ = ["InfoUpdateParams"]


class InfoUpdateParams(TypedDict, total=False):
    current_password: Optional[str]
    """The current user password."""

    email: Optional[str]
    """The user email."""

    name: Optional[str]
    """The user name."""

    password: Optional[str]
    """The new user password. If None, the user password is not changed."""
