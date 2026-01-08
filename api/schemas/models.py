from enum import Enum
from typing import Literal

from pydantic import Field

from api.schemas import BaseModel


class ModelCosts(BaseModel):
    prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class ModelType(str, Enum):
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"
    IMAGE_TO_TEXT = "image-to-text"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"


class Model(BaseModel):
    object: Literal["model"] = "model"
    id: str = Field(..., description="The model identifier, which can be referenced in the API endpoints.")
    type: ModelType = Field(..., description="The type of the model, which can be used to identify the model type.", examples=["text-generation"])  # fmt: off
    aliases: list[str] | None = Field(default=None, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    created: int = Field(..., description="Time of creation, as Unix timestamp.")
    owned_by: str = Field(..., description="The organization that owns the model.")
    max_context_length: int | None = Field(default=None, description="Maximum amount of tokens a context could contains. Makes sure it is the same for all models.")  # fmt: off
    costs: ModelCosts = Field(..., description="Costs of the model.")


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: list[Model]
