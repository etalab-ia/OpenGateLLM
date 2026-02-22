# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = ["LimitParam"]


class LimitParamTyped(TypedDict, total=False):
    router: Required[int]
    """The router ID."""

    type: Required[Literal["tpm", "tpd", "rpm", "rpd"]]
    """The limit type."""

    value: Optional[int]
    """The limit value."""


LimitParam: TypeAlias = Union[LimitParamTyped, Dict[str, object]]
