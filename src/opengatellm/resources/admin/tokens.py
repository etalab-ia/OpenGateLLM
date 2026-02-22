# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal

import httpx

from ..._types import Body, Omit, Query, Headers, NoneType, NotGiven, omit, not_given
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ...types.admin import token_list_params, token_create_params
from ..._base_client import make_request_options
from ...types.admin.token import Token
from ...types.admin.token_list_response import TokenListResponse
from ...types.admin.token_create_response import TokenCreateResponse

__all__ = ["TokensResource", "AsyncTokensResource"]


class TokensResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> TokensResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return TokensResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> TokensResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return TokensResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        name: str,
        user: int,
        expires: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> TokenCreateResponse:
        """
        Create a new token.

        Args:
          user: User ID to create the token for another user (by default, the current user).
              Required CREATE_USER permission.

          expires: Timestamp in seconds

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/admin/tokens",
            body=maybe_transform(
                {
                    "name": name,
                    "user": user,
                    "expires": expires,
                },
                token_create_params.TokenCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=TokenCreateResponse,
        )

    def retrieve(
        self,
        token: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Token:
        """
        Get your token by id.

        Args:
          token: The token ID of the token to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/admin/tokens/{token}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Token,
        )

    def list(
        self,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        order_by: Literal["id", "name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        user: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> TokenListResponse:
        """
        Get all your tokens.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          user: The user ID of the user to get the tokens for.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/admin/tokens",
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
                        "user": user,
                    },
                    token_list_params.TokenListParams,
                ),
            ),
            cast_to=TokenListResponse,
        )

    def delete(
        self,
        token: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a token.

        Args:
          token: The token ID of the token to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/v1/admin/tokens/{token}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncTokensResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncTokensResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncTokensResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncTokensResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncTokensResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        name: str,
        user: int,
        expires: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> TokenCreateResponse:
        """
        Create a new token.

        Args:
          user: User ID to create the token for another user (by default, the current user).
              Required CREATE_USER permission.

          expires: Timestamp in seconds

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/admin/tokens",
            body=await async_maybe_transform(
                {
                    "name": name,
                    "user": user,
                    "expires": expires,
                },
                token_create_params.TokenCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=TokenCreateResponse,
        )

    async def retrieve(
        self,
        token: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Token:
        """
        Get your token by id.

        Args:
          token: The token ID of the token to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/admin/tokens/{token}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Token,
        )

    async def list(
        self,
        *,
        limit: int | Omit = omit,
        offset: int | Omit = omit,
        order_by: Literal["id", "name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        user: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> TokenListResponse:
        """
        Get all your tokens.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          user: The user ID of the user to get the tokens for.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/admin/tokens",
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
                        "user": user,
                    },
                    token_list_params.TokenListParams,
                ),
            ),
            cast_to=TokenListResponse,
        )

    async def delete(
        self,
        token: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a token.

        Args:
          token: The token ID of the token to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/v1/admin/tokens/{token}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class TokensResourceWithRawResponse:
    def __init__(self, tokens: TokensResource) -> None:
        self._tokens = tokens

        self.create = to_raw_response_wrapper(
            tokens.create,
        )
        self.retrieve = to_raw_response_wrapper(
            tokens.retrieve,
        )
        self.list = to_raw_response_wrapper(
            tokens.list,
        )
        self.delete = to_raw_response_wrapper(
            tokens.delete,
        )


class AsyncTokensResourceWithRawResponse:
    def __init__(self, tokens: AsyncTokensResource) -> None:
        self._tokens = tokens

        self.create = async_to_raw_response_wrapper(
            tokens.create,
        )
        self.retrieve = async_to_raw_response_wrapper(
            tokens.retrieve,
        )
        self.list = async_to_raw_response_wrapper(
            tokens.list,
        )
        self.delete = async_to_raw_response_wrapper(
            tokens.delete,
        )


class TokensResourceWithStreamingResponse:
    def __init__(self, tokens: TokensResource) -> None:
        self._tokens = tokens

        self.create = to_streamed_response_wrapper(
            tokens.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            tokens.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            tokens.list,
        )
        self.delete = to_streamed_response_wrapper(
            tokens.delete,
        )


class AsyncTokensResourceWithStreamingResponse:
    def __init__(self, tokens: AsyncTokensResource) -> None:
        self._tokens = tokens

        self.create = async_to_streamed_response_wrapper(
            tokens.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            tokens.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            tokens.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            tokens.delete,
        )
