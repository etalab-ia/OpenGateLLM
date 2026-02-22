# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import Field as FieldInfo

from ..._models import BaseModel
from .model_type import ModelType
from .router_load_balancing_strategy import RouterLoadBalancingStrategy

__all__ = ["RouterCreateResponse"]


class RouterCreateResponse(BaseModel):
    id: int
    """ID of the created router."""

    name: str
    """Name of the model router."""

    type: ModelType
    """Type of the model router. It will be used to identify the model router type."""

    aliases: Optional[List[str]] = None
    """Aliases of the model. It will be used to identify the model by users."""

    cost_completion_tokens: Optional[float] = None
    """Cost of a million completion tokens (decrease user budget)"""

    cost_prompt_tokens: Optional[float] = None
    """Cost of a million prompt tokens (decrease user budget)"""

    load_balancing_strategy: Optional[RouterLoadBalancingStrategy] = None
    """Routing strategy for load balancing between providers of the model.

    It will be used to identify the model type.
    """

    if TYPE_CHECKING:
        # Some versions of Pydantic <2.8.0 have a bug and don’t allow assigning a
        # value to this field, so for compatibility we avoid doing it at runtime.
        __pydantic_extra__: Dict[str, object] = FieldInfo(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

        # Stub to indicate that arbitrary properties are accepted.
        # To access properties that are not valid identifiers you can use `getattr`, e.g.
        # `getattr(obj, '$type')`
        def __getattr__(self, attr: str) -> object: ...
    else:
        __pydantic_extra__: Dict[str, object]
