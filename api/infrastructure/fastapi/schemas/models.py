from enum import Enum
from typing import Literal

from pydantic import Field

from api.domain.router.entities import Model as ModelEntity
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


class Model(ModelEntity):
    object: Literal["model"] = "model"


class Models(BaseModel):
    object: Literal["list"] = "list"
    data: list[Model]
