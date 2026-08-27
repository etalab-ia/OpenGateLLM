from enum import StrEnum

from pydantic import Field

from api.domain import BaseModel, UtcDatetime


class ModelCosts(BaseModel):
    prompt_tokens: float = 0.0
    completion_tokens: float = 0.0


class ModelType(StrEnum):
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"
    IMAGE_TO_TEXT = "image-to-text"
    TEXT_CLASSIFICATION = "text-classification"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"


class ModelJsonResponse(BaseModel):
    def get_completions(self) -> list[str]:
        return []


class Model(BaseModel):
    id: str
    type: ModelType
    aliases: list[str] = []
    created: UtcDatetime
    owned_by: str
    max_context_length: int | None = None
    costs: ModelCosts = Field(default_factory=ModelCosts)


class Models(ModelJsonResponse):
    data: list[Model]


class HealthStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ModelHealthStatus(BaseModel):
    id: str
    status: HealthStatus
