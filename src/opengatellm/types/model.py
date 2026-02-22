# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from .._models import BaseModel
from .admin.model_type import ModelType

__all__ = ["Model", "Costs"]


class Costs(BaseModel):
    """Costs of the model."""

    completion_tokens: Optional[float] = None
    """Cost of a million completion tokens (decrease user budget)"""

    prompt_tokens: Optional[float] = None
    """Cost of a million prompt tokens (decrease user budget)"""


class Model(BaseModel):
    id: str
    """The model identifier, which can be referenced in the API endpoints."""

    costs: Costs
    """Costs of the model."""

    created: int
    """Time of creation, as Unix timestamp."""

    owned_by: str
    """The organization that owns the model."""

    type: ModelType
    """The type of the model, which can be used to identify the model type."""

    aliases: Optional[List[str]] = None
    """Aliases of the model. It will be used to identify the model by users."""

    max_context_length: Optional[int] = None
    """Maximum amount of tokens a context could contains.

    Makes sure it is the same for all models.
    """

    object: Optional[Literal["model"]] = None
