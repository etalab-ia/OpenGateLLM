# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Iterable

import httpx

from ..types import SearchMethod, search_perform_params
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
from .._base_client import make_request_options
from ..types.search_method import SearchMethod
from ..types.search_perform_response import SearchPerformResponse

__all__ = ["SearchResource", "AsyncSearchResource"]


class SearchResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> SearchResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return SearchResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> SearchResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return SearchResourceWithStreamingResponse(self)

    def perform(
        self,
        *,
        collections: Iterable[int],
        prompt: str,
        limit: int | Omit = omit,
        method: SearchMethod | Omit = omit,
        offset: int | Omit = omit,
        rff_k: int | Omit = omit,
        score_threshold: float | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> SearchPerformResponse:
        """
        Get relevant chunks from the collections and a query.

        Args:
          collections: List of collections ID

          prompt: Prompt related to the search

          limit: Number of results to return

          method: Search method to use

          offset: Offset for pagination, specifying how many results to skip from the beginning

          rff_k: Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search
              (recommended: from 10 to 100).

          score_threshold: Score of cosine similarity threshold for filtering results, only available for
              semantic search method.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/search",
            body=maybe_transform(
                {
                    "collections": collections,
                    "prompt": prompt,
                    "limit": limit,
                    "method": method,
                    "offset": offset,
                    "rff_k": rff_k,
                    "score_threshold": score_threshold,
                },
                search_perform_params.SearchPerformParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SearchPerformResponse,
        )


class AsyncSearchResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncSearchResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AsyncSearchResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncSearchResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AsyncSearchResourceWithStreamingResponse(self)

    async def perform(
        self,
        *,
        collections: Iterable[int],
        prompt: str,
        limit: int | Omit = omit,
        method: SearchMethod | Omit = omit,
        offset: int | Omit = omit,
        rff_k: int | Omit = omit,
        score_threshold: float | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> SearchPerformResponse:
        """
        Get relevant chunks from the collections and a query.

        Args:
          collections: List of collections ID

          prompt: Prompt related to the search

          limit: Number of results to return

          method: Search method to use

          offset: Offset for pagination, specifying how many results to skip from the beginning

          rff_k: Smoothing constant for Reciprocal Rank Fusion (RRF) algorithm in hybrid search
              (recommended: from 10 to 100).

          score_threshold: Score of cosine similarity threshold for filtering results, only available for
              semantic search method.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/search",
            body=await async_maybe_transform(
                {
                    "collections": collections,
                    "prompt": prompt,
                    "limit": limit,
                    "method": method,
                    "offset": offset,
                    "rff_k": rff_k,
                    "score_threshold": score_threshold,
                },
                search_perform_params.SearchPerformParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SearchPerformResponse,
        )


class SearchResourceWithRawResponse:
    def __init__(self, search: SearchResource) -> None:
        self._search = search

        self.perform = to_raw_response_wrapper(
            search.perform,
        )


class AsyncSearchResourceWithRawResponse:
    def __init__(self, search: AsyncSearchResource) -> None:
        self._search = search

        self.perform = async_to_raw_response_wrapper(
            search.perform,
        )


class SearchResourceWithStreamingResponse:
    def __init__(self, search: SearchResource) -> None:
        self._search = search

        self.perform = to_streamed_response_wrapper(
            search.perform,
        )


class AsyncSearchResourceWithStreamingResponse:
    def __init__(self, search: AsyncSearchResource) -> None:
        self._search = search

        self.perform = async_to_streamed_response_wrapper(
            search.perform,
        )
