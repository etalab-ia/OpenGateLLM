from typing import Annotated

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import Field, StringConstraints, field_validator

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class CreateChatCompletionsBody(BaseModel):
    messages: Annotated[list[dict], Field(description="A list of messages comprising the conversation so far.")]
    model: Annotated[Annotated[str, StringConstraints(min_length=1)], Field(description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `text-generation` model type is supported.")]  # fmt: off
    stream: Annotated[bool, Field(default=False, description="If set, partial message deltas will be sent. Tokens will be sent as data-only server-sent events as they become available, with the stream terminated by a data: [DONE] message.")]  # fmt: off

    @field_validator("stream", mode="before")
    def validate_stream(cls, stream: bool | None):
        if stream is None:
            return False
        return stream


class ChatCompletionResponse(ChatCompletion):
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]


class ChatCompletionChunkResponse(ChatCompletionChunk):
    usage: Annotated[Usage | None, Field(default=None, description="Usage information, sent on the last chunk of the stream.")]
