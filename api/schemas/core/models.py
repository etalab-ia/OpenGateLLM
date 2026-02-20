from enum import Enum
from http import HTTPMethod
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from api.utils import variables
from api.utils.variables import EndpointRoute

Endpoint = Enum("Endpoint", {name.upper(): value for name, value in vars(variables).items() if name.startswith("ENDPOINT__")}, type=str)


class ProviderEndpoints(BaseModel):
    audio_transcriptions: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]  # fmt: off
    chat_completions: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]
    embeddings: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]
    models: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]
    ocr: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]
    rerank: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^/", to_lower=True), Field(default=None)]

    def get_endpoint(self, endpoint: EndpointRoute) -> str | None:
        if endpoint == EndpointRoute.AUDIO_TRANSCRIPTIONS:
            return self.audio_transcriptions
        elif endpoint == EndpointRoute.CHAT_COMPLETIONS:
            return self.chat_completions
        elif endpoint == EndpointRoute.EMBEDDINGS:
            return self.embeddings
        elif endpoint == EndpointRoute.MODELS:
            return self.models
        elif endpoint == EndpointRoute.OCR:
            return self.ocr
        elif endpoint == EndpointRoute.RERANK:
            return self.rerank
        else:
            return None


class RequestContent(BaseModel):
    method: HTTPMethod
    model: str = Field(description="The called model name.")
    endpoint: Annotated[EndpointRoute, Field(description="The source endpoint (at the user side) of the request.")]
    json: dict = Field(default={}, description="The JSON body to use for the request.")
    form: dict = Field(default={}, description="The form-encoded data to use for the request.")
    files: dict = Field(default={}, description="The files to use for the request.")
    additional_data: dict = Field(default={}, description="The additional data to add to the response.")

    # @TODO: add a build method to build the request content from a request (after clean architecture refactor)


class Metric(str, Enum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric


# TEI
class TruncationDirection(Enum):
    left = "left"
    right = "right"


class TEICreateRerank(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: TruncationDirection = "right"
