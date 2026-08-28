from typing import Annotated, Literal

from pydantic import Field, model_validator

from api.domain import BaseModel
from api.domain.model.entities import ModelType
from api.domain.model.views import ModelView


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

    @model_validator(mode="before")
    @classmethod
    def from_model(cls, data):
        if isinstance(data, ModelView):
            return {
                "object": "model",
                "id": data.id,
                "type": data.type,
                "aliases": data.aliases,
                "created": int(data.created.timestamp()),
                "owned_by": data.owned_by,
                "max_context_length": data.max_context_length,
                "costs": {"prompt_tokens": data.costs.prompt_tokens, "completion_tokens": data.costs.completion_tokens},
            }
        return data


class ModelsResponse(BaseModel):
    object: Annotated[Literal["list"], Field("list", description="Type of the object.")]
    data: Annotated[list[Model], Field(..., description="List of models.")]
