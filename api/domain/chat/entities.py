from datetime import UTC, datetime
import json
from json import JSONDecodeError
from typing import Annotated, Any, Literal

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import Field

from api.domain import ForwardablePayload
from api.domain.model.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage


def _extract_text(content: Any) -> str:
    """Content is either a plain string or, on Mistral, a list of typed parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text") or "" for part in content if isinstance(part, dict) and part.get("type") == "text")

    return ""


class CreateChatCompletionsBody(ForwardablePayload):
    # only the union between OpenAI fields and vLLM fields is defined. See https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209
    messages: list[dict]
    model: str
    frequency_penalty: float | None = 0.0
    logit_bias: dict[str, float] | None = None
    logprobs: bool | None = False
    top_logprobs: int | None = None
    presence_penalty: float | None = 0.0
    max_completion_tokens: int | None = None
    n: int | None = 1
    response_format: Any | None = None
    seed: int | None = None
    stop: str | list[str] | None = None
    stream: bool = False
    stream_options: Any | None = None
    temperature: float | None = None
    top_p: float | None = None
    tools: list[dict] | None = None
    tool_choice: Any = "none"
    parallel_tool_calls: bool | None = False
    user: str | None = None

    def get_prompts(self) -> list[str]:
        return [text for message in self.messages if (text := _extract_text(message.get("content")))]


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
        choices = response.get("choices") or []

        result = ""
        for choice in choices:
            message = choice.get("message") or {}
            content = _extract_text(message.get("content"))
            reasoning_content = message.get("reasoning_content") or ""

            result += f"{content.strip()}\n" if content else ""
            result += f"{reasoning_content.strip()}\n" if isinstance(reasoning_content, str) and reasoning_content else ""

        return result.strip()


class ChatCompletionChunk(ChatCompletionChunk):
    @staticmethod
    def parse_chunk(chunk: str) -> Literal["[DONE]"] | dict | None:
        if not chunk.startswith("data: "):
            return None

        chunk = chunk.split("data: ")[1].strip()
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
        choices = chunk.get("choices") or []

        result = ""
        for choice in choices:
            delta = choice.get("delta") or {}
            content = _extract_text(delta.get("content"))
            reasoning_content = delta.get("reasoning_content") or ""

            result += f"{content.strip()}\n" if content else ""
            result += f"{reasoning_content.strip()}\n" if isinstance(reasoning_content, str) and reasoning_content else ""

        return result.strip()

    @staticmethod
    def build_usage_chunk(last_chunk: dict, request_id: str, model: str, usage: Usage) -> dict:
        fallback = {"object": "chat.completion.chunk", "created": int(datetime.now(tz=UTC).timestamp())}

        return {**fallback, **last_chunk, "choices": [], "id": request_id, "model": model, "usage": usage.model_dump()}
