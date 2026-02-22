# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

from ..._types import SequenceNotStr
from .model_type import ModelType
from .router_load_balancing_strategy import RouterLoadBalancingStrategy

__all__ = ["RouterUpdateParams"]


class RouterUpdateParams(TypedDict, total=False):
    aliases: Optional[SequenceNotStr[str]]
    """Aliases of the model. It will be used to identify the model by users."""

    cost_completion_tokens: Optional[float]
    """Cost of a million completion tokens (decrease user budget)"""

    cost_prompt_tokens: Optional[float]
    """Cost of a million prompt tokens (decrease user budget)"""

    load_balancing_strategy: Optional[RouterLoadBalancingStrategy]
    """Routing strategy for load balancing between providers of the model.

    It will be used to identify the model type.
    """

    name: Optional[str]
    """Name of the model router."""

    type: Optional[ModelType]
    """Type of the model router. It will be used to identify the model router type."""
