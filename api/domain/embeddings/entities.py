import array
import base64
from enum import StrEnum
from typing import Annotated, Any, Literal

from openai.types import CreateEmbeddingResponse
from openai.types.chat import ChatCompletionContentPartParam
from pydantic import Field

from api.domain import BaseModel, ForwardablePayload
from api.domain.chat.entities import _extract_text
from api.domain.model.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage


class EmbeddingMessage(BaseModel):
    role: Literal["system", "user", "assistant", "developer", "function", "tool"]
    content: str | list[ChatCompletionContentPartParam]


class EncodingFormat(StrEnum):
    FLOAT = "float"
    BASE64 = "base64"


class CreateEmbeddingsBody(ForwardablePayload):
    input: list[int] | list[list[int]] | str | list[str] | None
    messages: list[EmbeddingMessage] | None = None
    model: str
    encoding_format: EncodingFormat = EncodingFormat.FLOAT

    def get_prompts(self) -> list[str]:
        if isinstance(self.input, str):
            return [self.input]
        elif isinstance(self.input, list) and len(self.input) > 0:
            if isinstance(self.input[0], list):
                return [str(item) for sublist in self.input for item in sublist]
            else:
                return [str(item) for item in self.input]
        elif isinstance(self.messages, list) and len(self.messages) > 0:
            prompts = []
            for message in self.messages:
                prompts.append(_extract_text(message.model_dump(exclude_none=True)))
            return prompts
        else:
            return []


class Embeddings(CreateEmbeddingResponse, ProviderJsonResponse):
    object: Literal["list"] = "list"
    id: str
    model: str
    usage: Annotated[Usage, Field(default_factory=Usage)]

    @classmethod
    def _from_provider_response(
        cls,
        data: Any,
        *,
        encoding_format: EncodingFormat = EncodingFormat.FLOAT,
        id: str,
        model: str,
    ) -> "Embeddings":
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
        return cls(**{**data, "id": id, "model": model})
