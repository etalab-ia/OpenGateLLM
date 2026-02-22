# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal

import httpx

from ..._types import Body, Omit, Query, Headers, NoneType, NotGiven, SequenceNotStr, omit, not_given
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ...types.admin import (
    ModelType,
    RouterLoadBalancingStrategy,
    router_list_params,
    router_create_params,
    router_update_params,
)
from ..._base_client import make_request_options
from ...types.admin.router import Router
from ...types.admin.model_type import ModelType
from ...types.admin.router_list_response import RouterListResponse
from ...types.admin.router_create_response import RouterCreateResponse
from ...types.admin.router_load_balancing_strategy import RouterLoadBalancingStrategy

__all__ = ["RoutersResource", "AsyncRoutersResource"]


class RoutersResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> RoutersResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return RoutersResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> RoutersResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return RoutersResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        name: str,
        type: ModelType,
        aliases: SequenceNotStr[str] | Omit = omit,
        cost_completion_tokens: float | Omit = omit,
        cost_prompt_tokens: float | Omit = omit,
        load_balancing_strategy: RouterLoadBalancingStrategy | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RouterCreateResponse:
        """
        Create a router (without any providers).

        Args:
          name: Name of the model router.

          type: Type of the model router. It will be used to identify the model router type.

          aliases: Aliases of the model. It will be used to identify the model by users.

          cost_completion_tokens: Cost of a million completion tokens (decrease user budget)

          cost_prompt_tokens: Cost of a million prompt tokens (decrease user budget)

          load_balancing_strategy: Routing strategy for load balancing between providers of the model. It will be
              used to identify the model type.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/admin/routers",
            body=maybe_transform(
                {
                    "name": name,
                    "type": type,
                    "aliases": aliases,
                    "cost_completion_tokens": cost_completion_tokens,
                    "cost_prompt_tokens": cost_prompt_tokens,
                    "load_balancing_strategy": load_balancing_strategy,
                },
                router_create_params.RouterCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RouterCreateResponse,
        )

    def retrieve(
        self,
        router: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Router:
        """Get a router by ID.

        Args:
          router: The ID of the router to get (router ID, eg.

        123).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/admin/routers/{router}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Router,
        )

    def update(
        self,
        router: int,
        *,
        aliases: Optional[SequenceNotStr[str]] | Omit = omit,
        cost_completion_tokens: Optional[float] | Omit = omit,
        cost_prompt_tokens: Optional[float] | Omit = omit,
        load_balancing_strategy: Optional[RouterLoadBalancingStrategy] | Omit = omit,
        name: Optional[str] | Omit = omit,
        type: Optional[ModelType] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """Update a router.

        Args:
          router: The ID of the router to update (router ID, eg.

        123).

          aliases: Aliases of the model. It will be used to identify the model by users.

          cost_completion_tokens: Cost of a million completion tokens (decrease user budget)

          cost_prompt_tokens: Cost of a million prompt tokens (decrease user budget)

          load_balancing_strategy: Routing strategy for load balancing between providers of the model. It will be
              used to identify the model type.

          name: Name of the model router.

          type: Type of the model router. It will be used to identify the model router type.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._patch(
            f"/v1/admin/routers/{router}",
            body=maybe_transform(
                {
                    "aliases": aliases,
                    "cost_completion_tokens": cost_completion_tokens,
                    "cost_prompt_tokens": cost_prompt_tokens,
                    "load_balancing_strategy": load_balancing_strategy,
                    "name": name,
                    "type": type,
                },
                router_update_params.RouterUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )

    def list(
        self,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        order_by: Literal["id", "name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RouterListResponse:
        """
        Get all routers.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/admin/routers",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "limit": limit,
                        "offset": offset,
                        "order_by": order_by,
                        "order_direction": order_direction,
                    },
                    router_list_params.RouterListParams,
                ),
            ),
            cast_to=RouterListResponse,
        )

    def delete(
        self,
        router: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a model and all its providers.

        Args:
          router: The ID of the router to delete (router ID, eg. 123).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/v1/admin/routers/{router}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncRoutersResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncRoutersResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AsyncRoutersResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncRoutersResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AsyncRoutersResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        name: str,
        type: ModelType,
        aliases: SequenceNotStr[str] | Omit = omit,
        cost_completion_tokens: float | Omit = omit,
        cost_prompt_tokens: float | Omit = omit,
        load_balancing_strategy: RouterLoadBalancingStrategy | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RouterCreateResponse:
        """
        Create a router (without any providers).

        Args:
          name: Name of the model router.

          type: Type of the model router. It will be used to identify the model router type.

          aliases: Aliases of the model. It will be used to identify the model by users.

          cost_completion_tokens: Cost of a million completion tokens (decrease user budget)

          cost_prompt_tokens: Cost of a million prompt tokens (decrease user budget)

          load_balancing_strategy: Routing strategy for load balancing between providers of the model. It will be
              used to identify the model type.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/admin/routers",
            body=await async_maybe_transform(
                {
                    "name": name,
                    "type": type,
                    "aliases": aliases,
                    "cost_completion_tokens": cost_completion_tokens,
                    "cost_prompt_tokens": cost_prompt_tokens,
                    "load_balancing_strategy": load_balancing_strategy,
                },
                router_create_params.RouterCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RouterCreateResponse,
        )

    async def retrieve(
        self,
        router: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Router:
        """Get a router by ID.

        Args:
          router: The ID of the router to get (router ID, eg.

        123).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/admin/routers/{router}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Router,
        )

    async def update(
        self,
        router: int,
        *,
        aliases: Optional[SequenceNotStr[str]] | Omit = omit,
        cost_completion_tokens: Optional[float] | Omit = omit,
        cost_prompt_tokens: Optional[float] | Omit = omit,
        load_balancing_strategy: Optional[RouterLoadBalancingStrategy] | Omit = omit,
        name: Optional[str] | Omit = omit,
        type: Optional[ModelType] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """Update a router.

        Args:
          router: The ID of the router to update (router ID, eg.

        123).

          aliases: Aliases of the model. It will be used to identify the model by users.

          cost_completion_tokens: Cost of a million completion tokens (decrease user budget)

          cost_prompt_tokens: Cost of a million prompt tokens (decrease user budget)

          load_balancing_strategy: Routing strategy for load balancing between providers of the model. It will be
              used to identify the model type.

          name: Name of the model router.

          type: Type of the model router. It will be used to identify the model router type.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._patch(
            f"/v1/admin/routers/{router}",
            body=await async_maybe_transform(
                {
                    "aliases": aliases,
                    "cost_completion_tokens": cost_completion_tokens,
                    "cost_prompt_tokens": cost_prompt_tokens,
                    "load_balancing_strategy": load_balancing_strategy,
                    "name": name,
                    "type": type,
                },
                router_update_params.RouterUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )

    async def list(
        self,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        order_by: Literal["id", "name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RouterListResponse:
        """
        Get all routers.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/admin/routers",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform(
                    {
                        "limit": limit,
                        "offset": offset,
                        "order_by": order_by,
                        "order_direction": order_direction,
                    },
                    router_list_params.RouterListParams,
                ),
            ),
            cast_to=RouterListResponse,
        )

    async def delete(
        self,
        router: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a model and all its providers.

        Args:
          router: The ID of the router to delete (router ID, eg. 123).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/v1/admin/routers/{router}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class RoutersResourceWithRawResponse:
    def __init__(self, routers: RoutersResource) -> None:
        self._routers = routers

        self.create = to_raw_response_wrapper(
            routers.create,
        )
        self.retrieve = to_raw_response_wrapper(
            routers.retrieve,
        )
        self.update = to_raw_response_wrapper(
            routers.update,
        )
        self.list = to_raw_response_wrapper(
            routers.list,
        )
        self.delete = to_raw_response_wrapper(
            routers.delete,
        )


class AsyncRoutersResourceWithRawResponse:
    def __init__(self, routers: AsyncRoutersResource) -> None:
        self._routers = routers

        self.create = async_to_raw_response_wrapper(
            routers.create,
        )
        self.retrieve = async_to_raw_response_wrapper(
            routers.retrieve,
        )
        self.update = async_to_raw_response_wrapper(
            routers.update,
        )
        self.list = async_to_raw_response_wrapper(
            routers.list,
        )
        self.delete = async_to_raw_response_wrapper(
            routers.delete,
        )


class RoutersResourceWithStreamingResponse:
    def __init__(self, routers: RoutersResource) -> None:
        self._routers = routers

        self.create = to_streamed_response_wrapper(
            routers.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            routers.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            routers.update,
        )
        self.list = to_streamed_response_wrapper(
            routers.list,
        )
        self.delete = to_streamed_response_wrapper(
            routers.delete,
        )


class AsyncRoutersResourceWithStreamingResponse:
    def __init__(self, routers: AsyncRoutersResource) -> None:
        self._routers = routers

        self.create = async_to_streamed_response_wrapper(
            routers.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            routers.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            routers.update,
        )
        self.list = async_to_streamed_response_wrapper(
            routers.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            routers.delete,
        )
