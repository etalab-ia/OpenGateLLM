from enum import StrEnum
from typing import Annotated, Literal

from openai.types import CreateEmbeddingResponse
from pydantic import Field

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class EncodingFormat(StrEnum):
    FLOAT = "float"
    BASE64 = "base64"


class CreateEmbeddingsBody(BaseModel):
    input: Annotated[list[int] | list[Annotated[list[int], Field(min_length=1)]] | str | list[str], Field(min_length=1)] = Field(default=..., description="Input text to embed, encoded as a string or array of tokens. To embed multiple inputs in a single request, pass an array of strings or array of token arrays. The input must not exceed the max input tokens for the model (call `/v1/models` endpoint to get the `max_context_length` by model) and cannot be an empty string.")  # fmt: off
    model: str = Field(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `text-embeddings-inference` model type is supported.")  # fmt: off
    dimensions: int | None = Field(default=None, description="The number of dimensions the resulting output embeddings should have.")  # fmt: off
    encoding_format: EncodingFormat = Field(default=EncodingFormat.FLOAT, description="The format of the output embeddings.")  # fmt: off


class EmbeddingsResponse(CreateEmbeddingResponse):
    object: Literal["list"] = "list"
    id: str = Field(default=None, description="A unique identifier for the embedding.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
