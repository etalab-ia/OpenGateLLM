# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions

import httpx

from ..types import chunk_list_params
from .._types import Body, Omit, Query, Headers, NotGiven, omit, not_given
from .._utils import maybe_transform, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ..types.chunk import Chunk
from .._base_client import make_request_options
from ..types.chunk_list_response import ChunkListResponse

__all__ = ["ChunksResource", "AsyncChunksResource"]


class ChunksResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ChunksResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return ChunksResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ChunksResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return ChunksResourceWithStreamingResponse(self)

    @typing_extensions.deprecated("deprecated")
    def retrieve(
        self,
        chunk: int,
        *,
        document: int,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Chunk:
        """
        Get a chunk of a document.

        Args:
          document: The document ID

          chunk: The chunk ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/chunks/{document}/{chunk}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Chunk,
        )

    @typing_extensions.deprecated("deprecated")
    def list(
        self,
        document: int,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ChunkListResponse:
        """
        Get chunks of a document.

        Args:
          document: The document ID

          limit: The number of documents to return

          offset: The offset of the first document to return

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/chunks/{document}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "limit": limit,
                        "offset": offset,
                    },
                    chunk_list_params.ChunkListParams,
                ),
            ),
            cast_to=ChunkListResponse,
        )


class AsyncChunksResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncChunksResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncChunksResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncChunksResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncChunksResourceWithStreamingResponse(self)

    @typing_extensions.deprecated("deprecated")
    async def retrieve(
        self,
        chunk: int,
        *,
        document: int,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Chunk:
        """
        Get a chunk of a document.

        Args:
          document: The document ID

          chunk: The chunk ID

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/chunks/{document}/{chunk}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Chunk,
        )

    @typing_extensions.deprecated("deprecated")
    async def list(
        self,
        document: int,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ChunkListResponse:
        """
        Get chunks of a document.

        Args:
          document: The document ID

          limit: The number of documents to return

          offset: The offset of the first document to return

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/chunks/{document}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform(
                    {
                        "limit": limit,
                        "offset": offset,
                    },
                    chunk_list_params.ChunkListParams,
                ),
            ),
            cast_to=ChunkListResponse,
        )


class ChunksResourceWithRawResponse:
    def __init__(self, chunks: ChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_raw_response_wrapper(
                chunks.retrieve,  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            to_raw_response_wrapper(
                chunks.list,  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncChunksResourceWithRawResponse:
    def __init__(self, chunks: AsyncChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_raw_response_wrapper(
                chunks.retrieve,  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            async_to_raw_response_wrapper(
                chunks.list,  # pyright: ignore[reportDeprecated],
            )
        )


class ChunksResourceWithStreamingResponse:
    def __init__(self, chunks: ChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                chunks.retrieve,  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                chunks.list,  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncChunksResourceWithStreamingResponse:
    def __init__(self, chunks: AsyncChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                chunks.retrieve,  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                chunks.list,  # pyright: ignore[reportDeprecated],
            )
        )
