from datetime import UTC, datetime
import json
from json import JSONDecodeError
from typing import Annotated, Literal

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import Field

from api.domain import BaseModel, ForwardablePayload, UtcDatetime
from api.domain.model.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage


def _extract_text(message: dict) -> str:
    """Content is either a plain string or, on Mistral, a list of typed parts."""
    content = message.get("content") or ""
    if isinstance(content, str):
        content_text = content
    elif isinstance(content, list):  # Mistral format
        content_text = "".join(part.get("text") or "" for part in content if isinstance(part, dict) and part.get("type") == "text")
    else:
        content_text = ""

    reasoning_text = message.get("reasoning_content") or message.get("reasoning") or ""
    if not isinstance(reasoning_text, str):
        reasoning_text = ""

    return "\n".join(part for part in (content_text.strip(), reasoning_text.strip()) if part)


class CreateChatCompletionsBody(ForwardablePayload):
    messages: list[dict]
    model: str
    stream: bool = False

    def get_prompts(self) -> list[str]:
        return [text for message in self.messages if (text := _extract_text(message=message))]


class ChatCompletion(ChatCompletion, ProviderJsonResponse):
    id: Annotated[str, Field(default=None, description="A unique identifier for the chat completion.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]

    def get_completions(self) -> list[str]:
        content = self.extract_response_content(self.model_dump())

        return [content] if content else []

    @staticmethod
    def extract_response_content(response: dict) -> str:
        """
        Extract and concatenate the content and reasoning all choices content from a response to compute usage.
        Args:
            response (dict): The response to extract the content from. The response must be a valid JSON object.

        Returns:
            str: The concatenated content and reasoning choices content.
        """
        result = ""
        for choice in response.get("choices") or []:
            message = choice.get("message") or {}
            content = _extract_text(message=message)
            result += content

        return result


class ChatCompletionChunk(ChatCompletionChunk):
    @staticmethod
    def parse_chunk(chunk: str) -> Literal["[DONE]"] | dict | None:
        if not chunk.startswith("data: "):
            return None

        chunk = chunk.removeprefix("data: ").strip()
        if not chunk:
            return None
        if chunk == "[DONE]":
            return chunk
        try:
            return json.loads(chunk)
        except JSONDecodeError:
            return None

    @staticmethod
    def extract_chunk_content(chunk: dict) -> str:
        """
        Extract and concatenate the content and reasoning all choices content from a chunk to compute TTFT and usage.
        Args:
            chunk (dict): The chunk to extract the content from. The chunk must be a valid JSON object.

        Returns:
            str: The concatenated content and reasoning choices content.
        """
        result = ""
        for choice in chunk.get("choices") or []:
            message = choice.get("delta") or {}
            content = _extract_text(message=message)
            result += content

        return result

    @staticmethod
    def build_usage_chunk(last_chunk: dict, request_id: str, model: str, usage: Usage) -> dict:
        fallback = {"object": "chat.completion.chunk", "created": int(datetime.now(tz=UTC).timestamp())}

        return {**fallback, **last_chunk, "choices": [], "id": request_id, "model": model, "usage": usage.model_dump()}


class ChatCompletionStreamReader(BaseModel):
    """Reads a provider's chat completion stream one SSE line at a time: tells what to relay, and keeps what was delivered."""

    model: str
    request_id: str
    delivered_completions: list[str] = []
    last_delivered_chunk: dict | None = None
    provider_usage: Usage | None = None
    first_token_at: UtcDatetime | None = None
    has_reached_stream_end: bool = False

    @property
    def has_delivered_chunks(self) -> bool:
        return self.last_delivered_chunk is not None

    def read(self, line: str) -> str | None:
        """The line to relay, rewritten under the router name, or None when it must not reach the client."""
        chunk = ChatCompletionChunk.parse_chunk(chunk=line)
        if chunk == "[DONE]":
            self.has_reached_stream_end = True
            return None
        if chunk is None:
            return line

        if chunk.get("usage"):
            self.provider_usage = Usage.model_validate(chunk["usage"])
            if not chunk.get("choices"):
                return None

        self.last_delivered_chunk = chunk
        if content := ChatCompletionChunk.extract_chunk_content(chunk=chunk):
            self.delivered_completions.append(content)
            if self.first_token_at is None:
                self.first_token_at = datetime.now(tz=UTC)

        return f"data: {json.dumps({**chunk, 'model': self.model, 'id': self.request_id})}"

    def build_usage_line(self, usage: Usage) -> str:
        usage_chunk = ChatCompletionChunk.build_usage_chunk(
            last_chunk=self.last_delivered_chunk or {}, request_id=self.request_id, model=self.model, usage=usage
        )

        return f"data: {json.dumps(usage_chunk)}"
