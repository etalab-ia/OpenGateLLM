from enum import StrEnum
from typing import Literal

from openai.types import CreateEmbeddingResponse
from pydantic import Field

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class EncodingFormat(StrEnum):
    FLOAT = "float"
    BASE64 = "base64"


class CreateEmbeddingsBody(BaseModel):
    input: list[int] | list[list[int]] | str | list[str]
    model: str
    dimensions: int | None = None
    encoding_format: EncodingFormat = EncodingFormat.FLOAT

    def get_prompts(self) -> list[str]:
        if isinstance(self.input, str):
            return [self.input]
        elif isinstance(self.input, list):
            if isinstance(self.input[0], list):
                return [str(item) for sublist in self.input for item in sublist]
            else:
                return [str(item) for item in self.input]


class Embeddings(CreateEmbeddingResponse):
    object: Literal["list"] = "list"
    id: str = Field(default=None, description="A unique identifier for the embedding.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
