from http import HTTPMethod
from typing import Annotated

from pydantic import BaseModel, Field

from api.domain.model.entities import UserModelRequest
from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.schemas.audio import AudioTranscription
from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.schemas.embeddings import Embeddings
from api.schemas.ocr import OCR
from api.schemas.rerank import Reranks
from api.utils.variables import EndpointRoute


class OriginalModelRequest(BaseModel):
    endpoint: Annotated[EndpointRoute, Field(description="The source endpoint (at the user side) of the request.")]
    body: Annotated[dict, Field(default={}, description="The JSON body to use for the request.")]
    form: Annotated[dict, Field(default={}, description="The form-encoded data to use for the request.")]
    files: Annotated[dict, Field(default={}, description="The files to use for the request.")]

    @classmethod
    def from_user_request(cls, user_request: UserModelRequest) -> "OriginalModelRequest":
        return cls(
            endpoint=user_request.endpoint,
            body=user_request.body,
            form=user_request.form,
            files=user_request.files,
        )


class FormattedModelRequest(BaseModel):
    method: Annotated[HTTPMethod, Field(description="The HTTP method to build the request.")]
    url: Annotated[str, Field(description="The model API URL to build the request.")]
    body: Annotated[dict, Field(default={}, description="The JSON body to use for the request.")]
    form: Annotated[dict, Field(default={}, description="The form-encoded data to use for the request.")]
    files: Annotated[dict, Field(default={}, description="The files to use for the request.")]


class OriginalModelResponse(BaseModel):
    data: Annotated[dict | list, Field(default={}, description="The JSON data to use for the response.")]
    latency: Annotated[int | None, Field(default=None, description="The latency of the response.")]


class FormattedModelResponse(BaseModel):
    data: Annotated[AudioTranscription | ChatCompletion | ChatCompletionChunk | Embeddings | ModelsResponse | OCR | Reranks | None, Field(default=None, description="The JSON data to use for the response.")]  # fmt: off
    text: Annotated[str | None, Field(default=None, description="The text data to use for the response.")]


class ModelHttpExchange(BaseModel):
    original_request: OriginalModelRequest
    formatted_request: FormattedModelRequest | None = None
    original_response: OriginalModelResponse | None = None
    formatted_response: FormattedModelResponse | None = None
