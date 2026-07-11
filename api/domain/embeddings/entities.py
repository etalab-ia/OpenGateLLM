import array
import base64
from enum import StrEnum
from typing import Any, Literal

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

    @classmethod
    def _from_provider_response(cls, data: Any, *, encoding_format: EncodingFormat = EncodingFormat.FLOAT) -> "Embeddings":
        if isinstance(data, dict) and encoding_format == EncodingFormat.BASE64:
            data = {
                **data,
                "data": [
                    {
                        **item,
                        "embedding": (
                            array.array("f", base64.b64decode(item["embedding"])).tolist()
                            if isinstance(item.get("embedding"), str)
                            else item["embedding"]
                        ),
                    }
                    for item in data.get("data", [])
                ],
            }
        return cls(**data)
