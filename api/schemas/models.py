from enum import Enum
from typing import Literal

from openai.types import Model
from pydantic import Field

from api.schemas import BaseModel


class ModelCosts(BaseModel):
    prompt_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0, description="Cost of a million completion tokens (decrease user budget)")


class ModelType(str, Enum):
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"


class Model(Model):
    object: Literal["model"] = "model"
    max_context_length: int | None = None
    type: ModelType
    aliases: list[str] | None = []
    costs: dict[str, float] = Field(default_factory=dict)


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: list[Model]
