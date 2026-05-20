from typing import Annotated, Literal

from pydantic import Field

from api.domain.model.entities import ModelType
from api.infrastructure.fastapi.schemas import BaseModel


class ModelCosts(BaseModel):
    prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class Model(BaseModel):
    object: Annotated[Literal["model"], Field("model", description="Type of the object.")]
    id: Annotated[str, Field(..., description="The model identifier, which can be referenced in the API endpoints.")]
    type: Annotated[ModelType | None, Field(default=None, description="The type of the model, which can be used to identify the model type.", examples=["text-generation"])]  # fmt: off
    aliases: Annotated[list[str], Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])]  # fmt: off
    created: Annotated[int, Field(..., description="Time of creation, as Unix timestamp.")]
    owned_by: Annotated[str, Field(..., description="The organization that owns the model.")]
    max_context_length: Annotated[int | None, Field(default=None, description="Maximum amount of tokens a context could contains. Makes sure it is the same for all models.")]  # fmt: off
    costs: Annotated[ModelCosts, Field(default_factory=ModelCosts, description="Costs of the model.")]


class ModelsResponse(BaseModel):
    object: Annotated[Literal["list"], Field("list", description="Type of the object.")]
    data: Annotated[list[Model], Field(..., description="List of models.")]
