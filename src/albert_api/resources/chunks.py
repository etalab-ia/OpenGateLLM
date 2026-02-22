# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional

import httpx

from ..types import chunk_retrieve_params
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
from ..types.chunks import Chunks

__all__ = ["ChunksResource", "AsyncChunksResource"]


class ChunksResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ChunksResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#accessing-raw-response-data-eg-headers
        """
        return ChunksResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ChunksResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#with_streaming_response
        """
        return ChunksResourceWithStreamingResponse(self)

    def retrieve(
        self,
        document: str,
        *,
        collection: str,
        limit: Optional[int] | NotGiven = NOT_GIVEN,
        offset: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Chunks:
        """
        Get a single chunk.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not collection:
            raise ValueError(f"Expected a non-empty value for `collection` but received {collection!r}")
        if not document:
            raise ValueError(f"Expected a non-empty value for `document` but received {document!r}")
        return self._get(
            f"/v1/chunks/{collection}/{document}",
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
                    chunk_retrieve_params.ChunkRetrieveParams,
                ),
            ),
            cast_to=Chunks,
        )


class AsyncChunksResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncChunksResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#accessing-raw-response-data-eg-headers
        """
        return AsyncChunksResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncChunksResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/albert-api-python#with_streaming_response
        """
        return AsyncChunksResourceWithStreamingResponse(self)

    async def retrieve(
        self,
        document: str,
        *,
        collection: str,
        limit: Optional[int] | NotGiven = NOT_GIVEN,
        offset: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Chunks:
        """
        Get a single chunk.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not collection:
            raise ValueError(f"Expected a non-empty value for `collection` but received {collection!r}")
        if not document:
            raise ValueError(f"Expected a non-empty value for `document` but received {document!r}")
        return await self._get(
            f"/v1/chunks/{collection}/{document}",
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
                    chunk_retrieve_params.ChunkRetrieveParams,
                ),
            ),
            cast_to=Chunks,
        )


class ChunksResourceWithRawResponse:
    def __init__(self, chunks: ChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = to_raw_response_wrapper(
            chunks.retrieve,
        )


class AsyncChunksResourceWithRawResponse:
    def __init__(self, chunks: AsyncChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = async_to_raw_response_wrapper(
            chunks.retrieve,
        )


class ChunksResourceWithStreamingResponse:
    def __init__(self, chunks: ChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = to_streamed_response_wrapper(
            chunks.retrieve,
        )


class AsyncChunksResourceWithStreamingResponse:
    def __init__(self, chunks: AsyncChunksResource) -> None:
        self._chunks = chunks

        self.retrieve = async_to_streamed_response_wrapper(
            chunks.retrieve,
        )
