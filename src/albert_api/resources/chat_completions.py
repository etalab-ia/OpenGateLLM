# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Any, List, Union, Iterable, Optional, cast
from typing_extensions import Literal

import httpx

from ..types import chat_completion_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import (
    maybe_transform,
    async_maybe_transform,
)
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

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#accessing-raw-response-data-eg-headers
        """
        return ChatCompletionsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ChatCompletionsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#with_streaming_response
        """
        return ChatCompletionsResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        messages: Iterable[chat_completion_create_params.Message],
        model: str,
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        min_p: float | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[str, List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[True, False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[chat_completion_create_params.ToolChoice] | NotGiven = NOT_GIVEN,
        tools: Iterable[chat_completion_create_params.Tool] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
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

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#accessing-raw-response-data-eg-headers
        """
        return AsyncChatCompletionsResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncChatCompletionsResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#with_streaming_response
        """
        return AsyncChatCompletionsResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        messages: Iterable[chat_completion_create_params.Message],
        model: str,
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        min_p: float | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[str, List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[True, False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[chat_completion_create_params.ToolChoice] | NotGiven = NOT_GIVEN,
        tools: Iterable[chat_completion_create_params.Tool] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
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
