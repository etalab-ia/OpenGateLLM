import logging

import tiktoken

from api.schemas.chat import ChatCompletion, ChatCompletionChunk
from api.schemas.core.configuration import Tokenizer
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


class UsageTokenizer:
    USAGE_ENDPOINTS = [EndpointRoute.CHAT_COMPLETIONS, EndpointRoute.EMBEDDINGS, EndpointRoute.OCR, EndpointRoute.RERANK, EndpointRoute.SEARCH]

    def __init__(self, tokenizer: Tokenizer):
        if tokenizer == Tokenizer.TIKTOKEN_O200K_BASE:
            self.tokenizer = tiktoken.get_encoding("o200k_base")
        elif tokenizer == Tokenizer.TIKTOKEN_P50K_BASE:
            self.tokenizer = tiktoken.get_encoding("p50k_base")
        elif tokenizer == Tokenizer.TIKTOKEN_R50K_BASE:
            self.tokenizer = tiktoken.get_encoding("r50k_base")
        elif tokenizer == Tokenizer.TIKTOKEN_P50K_EDIT:
            self.tokenizer = tiktoken.get_encoding("p50k_edit")
        elif tokenizer == Tokenizer.TIKTOKEN_CL100K_BASE:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        elif tokenizer == Tokenizer.TIKTOKEN_GPT2:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def get_prompt_tokens(self, endpoint: str, body: dict) -> int:
        try:
            if endpoint == EndpointRoute.CHAT_COMPLETIONS:
                contents = [message.get("content") for message in body["messages"] if message.get("content")]
                prompt_tokens = sum([len(self.tokenizer.encode(content)) for content in contents])

            elif endpoint == EndpointRoute.EMBEDDINGS:
                prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

            elif endpoint == EndpointRoute.RERANK:
                prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

            elif endpoint == EndpointRoute.SEARCH:
                prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))

            elif endpoint == EndpointRoute.OCR:
                prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))
            else:
                prompt_tokens = 0

        except Exception:  # to avoid request format error before schema validation
            prompt_tokens = 0

        return prompt_tokens

    def get_completion_tokens(self, endpoint: str, response_data: dict | list[dict]) -> int:
        """
        Get the completion tokens for the given endpoint and body.

        Args:
            endpoint (str): The endpoint to get the completion tokens for.
            response_data (dict | list[dict]): The response data of the request (must be a ChatCompletion or a list of ChatCompletionChunk).
        """
        completion_tokens = 0
        if endpoint == EndpointRoute.CHAT_COMPLETIONS:
            if isinstance(response_data, list):
                completion_tokens = sum([len(self.tokenizer.encode(ChatCompletionChunk.extract_chunk_content(chunk=chunk))) for chunk in response_data])  # fmt: off
            else:
                completion_tokens = len(self.tokenizer.encode(ChatCompletion.extract_response_content(response=response_data)))

        return completion_tokens
