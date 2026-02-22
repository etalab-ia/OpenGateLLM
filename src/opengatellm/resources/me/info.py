# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional

import httpx

from ..._types import Body, Omit, Query, Headers, NoneType, NotGiven, omit, not_given
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ...types.me import info_update_params
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ..._base_client import make_request_options
from ...types.me.info_retrieve_response import InfoRetrieveResponse

__all__ = ["InfoResource", "AsyncInfoResource"]


class InfoResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> InfoResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return InfoResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> InfoResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return InfoResourceWithStreamingResponse(self)

    def retrieve(
        self,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> InfoRetrieveResponse:
        """Get information about the current user."""
        return self._get(
            "/v1/me/info",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=InfoRetrieveResponse,
        )

    def update(
        self,
        *,
        current_password: Optional[str] | Omit = omit,
        email: Optional[str] | Omit = omit,
        name: Optional[str] | Omit = omit,
        password: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update information about the current user.

        Args:
          current_password: The current user password.

          email: The user email.

          name: The user name.

          password: The new user password. If None, the user password is not changed.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._patch(
            "/v1/me/info",
            body=maybe_transform(
                {
                    "current_password": current_password,
                    "email": email,
                    "name": name,
                    "password": password,
                },
                info_update_params.InfoUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncInfoResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncInfoResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncInfoResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncInfoResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncInfoResourceWithStreamingResponse(self)

    async def retrieve(
        self,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> InfoRetrieveResponse:
        """Get information about the current user."""
        return await self._get(
            "/v1/me/info",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=InfoRetrieveResponse,
        )

    async def update(
        self,
        *,
        current_password: Optional[str] | Omit = omit,
        email: Optional[str] | Omit = omit,
        name: Optional[str] | Omit = omit,
        password: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update information about the current user.

        Args:
          current_password: The current user password.

          email: The user email.

          name: The user name.

          password: The new user password. If None, the user password is not changed.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._patch(
            "/v1/me/info",
            body=await async_maybe_transform(
                {
                    "current_password": current_password,
                    "email": email,
                    "name": name,
                    "password": password,
                },
                info_update_params.InfoUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class InfoResourceWithRawResponse:
    def __init__(self, info: InfoResource) -> None:
        self._info = info

        self.retrieve = to_raw_response_wrapper(
            info.retrieve,
        )
        self.update = to_raw_response_wrapper(
            info.update,
        )


class AsyncInfoResourceWithRawResponse:
    def __init__(self, info: AsyncInfoResource) -> None:
        self._info = info

        self.retrieve = async_to_raw_response_wrapper(
            info.retrieve,
        )
        self.update = async_to_raw_response_wrapper(
            info.update,
        )


class InfoResourceWithStreamingResponse:
    def __init__(self, info: InfoResource) -> None:
        self._info = info

        self.retrieve = to_streamed_response_wrapper(
            info.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            info.update,
        )


class AsyncInfoResourceWithStreamingResponse:
    def __init__(self, info: AsyncInfoResource) -> None:
        self._info = info

        self.retrieve = async_to_streamed_response_wrapper(
            info.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            info.update,
        )
