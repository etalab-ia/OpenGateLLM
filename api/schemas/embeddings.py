from enum import StrEnum
from typing import Literal

from openai.types import CreateEmbeddingResponse
from pydantic import Field, field_validator

from api.schemas import BaseModel
from api.schemas.usage import Usage


class EncodingFormat(StrEnum):
    FLOAT = "float"
    BASE64 = "base64"


class EmbeddingsRequest(BaseModel):
    input: list[int] | list[list[int]] | str | list[str] = Field(default=..., description="Input text to embed, encoded as a string or array of tokens. To embed multiple inputs in a single request, pass an array of strings or array of token arrays. The input must not exceed the max input tokens for the model (call `/v1/models` endpoint to get the `max_context_length` by model) and cannot be an empty string.")  # fmt: off
    model: str = Field(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `text-embeddings-inference` model type is supported.")  # fmt: off
    dimensions: int | None = Field(default=None, description="The number of dimensions the resulting output embeddings should have.")  # fmt: off
    encoding_format: EncodingFormat = Field(default=EncodingFormat.FLOAT, description="The format of the output embeddings.")  # fmt: off

    # TODO: delete validation for input (replace by Annotated[list[int], Field(min_length=1)])
    @field_validator("input")
    def validate_input(cls, input):
        assert input, "Input must not be an empty object."
        return input


class Embeddings(CreateEmbeddingResponse):
    object: Literal["list"] = "list"
    id: str = Field(default=None, description="A unique identifier for the embedding.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
