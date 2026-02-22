# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Iterable, Optional
from typing_extensions import TypedDict

from .limit_param import LimitParam
from .permission_type import PermissionType

__all__ = ["RoleUpdateParams"]


class RoleUpdateParams(TypedDict, total=False):
    limits: Optional[Iterable[LimitParam]]
    """The new limits."""

    name: Optional[str]
    """The new role name."""

    permissions: Optional[List[PermissionType]]
    """The new permissions."""
