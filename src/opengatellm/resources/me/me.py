# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal

import httpx

from .info import (
    InfoResource,
    AsyncInfoResource,
    InfoResourceWithRawResponse,
    AsyncInfoResourceWithRawResponse,
    InfoResourceWithStreamingResponse,
    AsyncInfoResourceWithStreamingResponse,
)
from .keys import (
    KeysResource,
    AsyncKeysResource,
    KeysResourceWithRawResponse,
    AsyncKeysResourceWithRawResponse,
    KeysResourceWithStreamingResponse,
    AsyncKeysResourceWithStreamingResponse,
)
from ...types import me_get_usage_params
from ..._types import Body, Omit, Query, Headers, NotGiven, omit, not_given
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ..._base_client import make_request_options
from ...types.me_get_usage_response import MeGetUsageResponse

__all__ = ["MeResource", "AsyncMeResource"]


class MeResource(SyncAPIResource):
    @cached_property
    def info(self) -> InfoResource:
        return InfoResource(self._client)

    @cached_property
    def keys(self) -> KeysResource:
        return KeysResource(self._client)

    @cached_property
    def with_raw_response(self) -> MeResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return MeResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> MeResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return MeResourceWithStreamingResponse(self)

    def get_usage(
        self,
        *,
        end_time: Optional[int] | Omit = omit,
        endpoint: Optional[
            Literal[
                "/v1/audio/transcriptions",
                "/v1/chat/completions",
                "/v1/embeddings",
                "/v1/ocr",
                "/v1/rerank",
                "/v1/search",
            ]
        ]
        | Omit = omit,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        start_time: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> MeGetUsageResponse:
        """
        Get usage for the current user.

        Args:
          end_time: End time as Unix timestamp (if not provided, will be set to now)

          endpoint: The endpoint to get usage for.

          limit: The limit of the usages to get.

          offset: The offset of the usages to get.

          start_time: Start time as Unix timestamp (if not provided, will be set to 30 days ago)

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/me/usage",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "end_time": end_time,
                        "endpoint": endpoint,
                        "limit": limit,
                        "offset": offset,
                        "start_time": start_time,
                    },
                    me_get_usage_params.MeGetUsageParams,
                ),
            ),
            cast_to=MeGetUsageResponse,
        )


class AsyncMeResource(AsyncAPIResource):
    @cached_property
    def info(self) -> AsyncInfoResource:
        return AsyncInfoResource(self._client)

    @cached_property
    def keys(self) -> AsyncKeysResource:
        return AsyncKeysResource(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncMeResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AsyncMeResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncMeResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AsyncMeResourceWithStreamingResponse(self)

    async def get_usage(
        self,
        *,
        end_time: Optional[int] | Omit = omit,
        endpoint: Optional[
            Literal[
                "/v1/audio/transcriptions",
                "/v1/chat/completions",
                "/v1/embeddings",
                "/v1/ocr",
                "/v1/rerank",
                "/v1/search",
            ]
        ]
        | Omit = omit,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        start_time: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> MeGetUsageResponse:
        """
        Get usage for the current user.

        Args:
          end_time: End time as Unix timestamp (if not provided, will be set to now)

          endpoint: The endpoint to get usage for.

          limit: The limit of the usages to get.

          offset: The offset of the usages to get.

          start_time: Start time as Unix timestamp (if not provided, will be set to 30 days ago)

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/me/usage",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform(
                    {
                        "end_time": end_time,
                        "endpoint": endpoint,
                        "limit": limit,
                        "offset": offset,
                        "start_time": start_time,
                    },
                    me_get_usage_params.MeGetUsageParams,
                ),
            ),
            cast_to=MeGetUsageResponse,
        )


class MeResourceWithRawResponse:
    def __init__(self, me: MeResource) -> None:
        self._me = me

        self.get_usage = to_raw_response_wrapper(
            me.get_usage,
        )

    @cached_property
    def info(self) -> InfoResourceWithRawResponse:
        return InfoResourceWithRawResponse(self._me.info)

    @cached_property
    def keys(self) -> KeysResourceWithRawResponse:
        return KeysResourceWithRawResponse(self._me.keys)


class AsyncMeResourceWithRawResponse:
    def __init__(self, me: AsyncMeResource) -> None:
        self._me = me

        self.get_usage = async_to_raw_response_wrapper(
            me.get_usage,
        )

    @cached_property
    def info(self) -> AsyncInfoResourceWithRawResponse:
        return AsyncInfoResourceWithRawResponse(self._me.info)

    @cached_property
    def keys(self) -> AsyncKeysResourceWithRawResponse:
        return AsyncKeysResourceWithRawResponse(self._me.keys)


class MeResourceWithStreamingResponse:
    def __init__(self, me: MeResource) -> None:
        self._me = me

        self.get_usage = to_streamed_response_wrapper(
            me.get_usage,
        )

    @cached_property
    def info(self) -> InfoResourceWithStreamingResponse:
        return InfoResourceWithStreamingResponse(self._me.info)

    @cached_property
    def keys(self) -> KeysResourceWithStreamingResponse:
        return KeysResourceWithStreamingResponse(self._me.keys)


class AsyncMeResourceWithStreamingResponse:
    def __init__(self, me: AsyncMeResource) -> None:
        self._me = me

        self.get_usage = async_to_streamed_response_wrapper(
            me.get_usage,
        )

    @cached_property
    def info(self) -> AsyncInfoResourceWithStreamingResponse:
        return AsyncInfoResourceWithStreamingResponse(self._me.info)

    @cached_property
    def keys(self) -> AsyncKeysResourceWithStreamingResponse:
        return AsyncKeysResourceWithStreamingResponse(self._me.keys)
