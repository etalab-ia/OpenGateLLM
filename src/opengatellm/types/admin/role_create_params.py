# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Iterable, Optional
from typing_extensions import Required, TypedDict

from .limit_param import LimitParam
from .permission_type import PermissionType

__all__ = ["RoleCreateParams"]


class RoleCreateParams(TypedDict, total=False):
    name: Required[str]

    limits: Iterable[LimitParam]

    permissions: Optional[List[PermissionType]]
