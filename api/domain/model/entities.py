from enum import StrEnum

from pydantic import BaseModel, Field

from api.utils.variables import EndpointRoute


class Metric(StrEnum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric


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


class Model(BaseModel):
    id: str
    type: ModelType
    aliases: list[str] = []
    created: int
    owned_by: str
    max_context_length: int | None = None
    costs: ModelCosts


class UserModelRequest(BaseModel):
    endpoint: EndpointRoute
    body: dict = Field(default={}, description="The JSON body to use for the request.")
    form: dict = Field(default={}, description="The form-encoded data to use for the request.")
    files: dict = Field(default={}, description="The files to use for the request.")
