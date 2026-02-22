# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

import builtins
from typing import TYPE_CHECKING, Dict, List, Optional
from typing_extensions import Literal

from pydantic import Field as FieldInfo

from ..._models import BaseModel
from .model_type import ModelType
from .router_load_balancing_strategy import RouterLoadBalancingStrategy

__all__ = ["Router"]


class Router(BaseModel):
    id: int
    """ID of the router."""

    cost_completion_tokens: float
    """Cost of a million completion tokens (decrease user budget)"""

    cost_prompt_tokens: float
    """Cost of a million prompt tokens (decrease user budget)"""

    created: int
    """Time of creation, as Unix timestamp."""

    load_balancing_strategy: RouterLoadBalancingStrategy
    """Routing strategy for load balancing between providers of the model.

    It will be used to identify the model type.
    """

    name: str
    """Name of the router."""

    type: ModelType
    """Type of the model router. It will be used to identify the model router type."""

    updated: int
    """Time of last update, as Unix timestamp."""

    user_id: int
    """ID of the user that owns the router."""

    aliases: Optional[List[str]] = None
    """Aliases of the model. It will be used to identify the model by users."""

    max_context_length: Optional[int] = None
    """Maximum amount of tokens a context could contains.

    Make sure it is the same for all models.
    """

    object: Optional[Literal["router"]] = None

    providers: Optional[int] = None
    """Number of providers in the router."""

    vector_size: Optional[int] = None
    """Dimension of the vectors, if the models are embeddings.

    Make sure it is the same for all models.
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
