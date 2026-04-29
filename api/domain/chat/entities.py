import json
from json import JSONDecodeError
from typing import Literal

from openai.types.chat import ChatCompletion, ChatCompletionChunk
from pydantic import Field

from api.domain.usage.entities import Usage


class ChatCompletion(ChatCompletion):
    id: str = Field(default=None, description="A unique identifier for the chat completion.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")

    @staticmethod
    def extract_response_content(response: dict) -> str:
        """
        Extract and concatenate the content and reasoning all choices content from a response to compute usage.
        Args:
            chunk (dict): The chunk to extract the content from. The chunk must be a valid JSON object.

        Returns:
            str: The concatenated content and reasoning choices content.
        """
        choices = response.get("choices") or []
        if len(choices) == 0:
            return ""

        result = ""
        for choice in choices:
            choice = choices[0]
            message = choice.get("message") or {}
            content = message.get("content") or ""
            reasoning_content = message.get("reasoning_content") or ""

            result += f"{content.strip()}\n" if content else ""
            result += f"{reasoning_content.strip()}\n" if reasoning_content else ""

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
        if len(choices) == 0:
            return ""

        result = ""
        for choice in choices:
            delta = choice.get("delta") or {}
            content = delta.get("content") or ""
            reasoning_content = delta.get("reasoning_content") or ""

            result += f"{content.strip()}\n" if content else ""
            result += f"{reasoning_content.strip()}\n" if reasoning_content else ""

        return result.strip()
