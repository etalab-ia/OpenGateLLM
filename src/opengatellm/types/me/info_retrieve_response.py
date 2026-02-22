# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

import builtins
from typing import TYPE_CHECKING, Dict, List, Optional
from typing_extensions import Literal

from pydantic import Field as FieldInfo

from ..._models import BaseModel
from ..admin.limit import Limit
from ..admin.permission_type import PermissionType

__all__ = ["InfoRetrieveResponse"]


class InfoRetrieveResponse(BaseModel):
    id: int
    """The user ID."""

    created: int
    """The user creation timestamp."""

    email: str
    """The user email."""

    limits: List[Limit]
    """The user rate limits."""

    permissions: List[PermissionType]
    """The user permissions."""

    updated: int
    """The user update timestamp."""

    budget: Optional[float] = None
    """The user budget. If None, the user has unlimited budget."""

    expires: Optional[int] = None
    """The user expiration timestamp. If None, the user will never expire."""

    name: Optional[str] = None
    """The user name."""

    object: Optional[Literal["userInfo"]] = None
    """The user info object type."""

    organization: Optional[int] = None
    """The user organization ID."""

    priority: Optional[int] = None
    """The user priority (higher = higher priority).

    This value influences scheduling/queue priority for non-streaming model
    invocations.
    """

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, builtins.object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> builtins.object: ...
    else:
        __pydantic_extra__: Dict[str, builtins.object]
