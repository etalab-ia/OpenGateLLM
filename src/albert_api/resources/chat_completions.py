# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Any, Union, Iterable, Optional, cast
from typing_extensions import Literal

import httpx

from ..types import chat_completion_create_params
from .._types import Body, Omit, Query, Headers, NotGiven, SequenceNotStr, omit, not_given
from .._utils import maybe_transform, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from .._base_client import make_request_options
from ..types.chat_completion_create_response import ChatCompletionCreateResponse

__all__ = ["ChatCompletionsResource", "AsyncChatCompletionsResource"]


class ChatCompletionsResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ChatCompletionsResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return ChatCompletionsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ChatCompletionsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return ChatCompletionsResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        messages: Iterable[chat_completion_create_params.Message],
        model: str,
        best_of: Optional[int] | Omit = omit,
        frequency_penalty: Optional[float] | Omit = omit,
        max_tokens: Optional[int] | Omit = omit,
        min_p: float | Omit = omit,
        n: Optional[int] | Omit = omit,
        presence_penalty: Optional[float] | Omit = omit,
        seed: Optional[int] | Omit = omit,
        stop: Union[str, SequenceNotStr[str], None] | Omit = omit,
        stream: Optional[Literal[True, False]] | Omit = omit,
        temperature: Optional[float] | Omit = omit,
        tool_choice: Optional[chat_completion_create_params.ToolChoice] | Omit = omit,
        tools: Iterable[chat_completion_create_params.Tool] | Omit = omit,
        top_k: int | Omit = omit,
        top_p: Optional[float] | Omit = omit,
        user: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ChatCompletionCreateResponse:
        """Completion API similar to OpenAI's API.

        See
        https://platform.openai.com/docs/api-reference/chat/create for the API
        specification.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return cast(
            ChatCompletionCreateResponse,
            self._post(
                "/v1/chat/completions",
                body=maybe_transform(
                    {
                        "messages": messages,
                        "model": model,
                        "best_of": best_of,
                        "frequency_penalty": frequency_penalty,
                        "max_tokens": max_tokens,
                        "min_p": min_p,
                        "n": n,
                        "presence_penalty": presence_penalty,
                        "seed": seed,
                        "stop": stop,
                        "stream": stream,
                        "temperature": temperature,
                        "tool_choice": tool_choice,
                        "tools": tools,
                        "top_k": top_k,
                        "top_p": top_p,
                        "user": user,
                    },
                    chat_completion_create_params.ChatCompletionCreateParams,
                ),
                options=make_request_options(
                    extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
                ),
                cast_to=cast(
                    Any, ChatCompletionCreateResponse
                ),  # Union types cannot be passed in as arguments in the type system
            ),
        )


class AsyncChatCompletionsResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncChatCompletionsResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AsyncChatCompletionsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncChatCompletionsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AsyncChatCompletionsResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        messages: Iterable[chat_completion_create_params.Message],
        model: str,
        best_of: Optional[int] | Omit = omit,
        frequency_penalty: Optional[float] | Omit = omit,
        max_tokens: Optional[int] | Omit = omit,
        min_p: float | Omit = omit,
        n: Optional[int] | Omit = omit,
        presence_penalty: Optional[float] | Omit = omit,
        seed: Optional[int] | Omit = omit,
        stop: Union[str, SequenceNotStr[str], None] | Omit = omit,
        stream: Optional[Literal[True, False]] | Omit = omit,
        temperature: Optional[float] | Omit = omit,
        tool_choice: Optional[chat_completion_create_params.ToolChoice] | Omit = omit,
        tools: Iterable[chat_completion_create_params.Tool] | Omit = omit,
        top_k: int | Omit = omit,
        top_p: Optional[float] | Omit = omit,
        user: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ChatCompletionCreateResponse:
        """Completion API similar to OpenAI's API.

        See
        https://platform.openai.com/docs/api-reference/chat/create for the API
        specification.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return cast(
            ChatCompletionCreateResponse,
            await self._post(
                "/v1/chat/completions",
                body=await async_maybe_transform(
                    {
                        "messages": messages,
                        "model": model,
                        "best_of": best_of,
                        "frequency_penalty": frequency_penalty,
                        "max_tokens": max_tokens,
                        "min_p": min_p,
                        "n": n,
                        "presence_penalty": presence_penalty,
                        "seed": seed,
                        "stop": stop,
                        "stream": stream,
                        "temperature": temperature,
                        "tool_choice": tool_choice,
                        "tools": tools,
                        "top_k": top_k,
                        "top_p": top_p,
                        "user": user,
                    },
                    chat_completion_create_params.ChatCompletionCreateParams,
                ),
                options=make_request_options(
                    extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
                ),
                cast_to=cast(
                    Any, ChatCompletionCreateResponse
                ),  # Union types cannot be passed in as arguments in the type system
            ),
        )


class ChatCompletionsResourceWithRawResponse:
    def __init__(self, chat_completions: ChatCompletionsResource) -> None:
        self._chat_completions = chat_completions

        self.create = to_raw_response_wrapper(
            chat_completions.create,
        )


class AsyncChatCompletionsResourceWithRawResponse:
    def __init__(self, chat_completions: AsyncChatCompletionsResource) -> None:
        self._chat_completions = chat_completions

        self.create = async_to_raw_response_wrapper(
            chat_completions.create,
        )


class ChatCompletionsResourceWithStreamingResponse:
    def __init__(self, chat_completions: ChatCompletionsResource) -> None:
        self._chat_completions = chat_completions

        self.create = to_streamed_response_wrapper(
            chat_completions.create,
        )


class AsyncChatCompletionsResourceWithStreamingResponse:
    def __init__(self, chat_completions: AsyncChatCompletionsResource) -> None:
        self._chat_completions = chat_completions

        self.create = async_to_streamed_response_wrapper(
            chat_completions.create,
        )
