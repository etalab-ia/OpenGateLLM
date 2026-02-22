# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Iterable, Optional
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
from ...types.admin import role_list_params, role_create_params, role_update_params
from ..._base_client import make_request_options
from ...types.admin.role import Role
from ...types.admin.limit_param import LimitParam
from ...types.admin.permission_type import PermissionType
from ...types.admin.role_list_response import RoleListResponse
from ...types.admin.role_create_response import RoleCreateResponse

__all__ = ["RolesResource", "AsyncRolesResource"]


class RolesResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> RolesResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return RolesResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> RolesResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return RolesResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        name: str,
        limits: Iterable[LimitParam] | Omit = omit,
        permissions: Optional[List[PermissionType]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RoleCreateResponse:
        """
        Create a new role.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/admin/roles",
            body=maybe_transform(
                {
                    "name": name,
                    "limits": limits,
                    "permissions": permissions,
                },
                role_create_params.RoleCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RoleCreateResponse,
        )

    def retrieve(
        self,
        role: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Role:
        """
        Get a role by id.

        Args:
          role: The ID of the role to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/admin/roles/{role}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Role,
        )

    def update(
        self,
        role: int,
        *,
        limits: Optional[Iterable[LimitParam]] | Omit = omit,
        name: Optional[str] | Omit = omit,
        permissions: Optional[List[PermissionType]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update a role.

        Args:
          role: The ID of the role to update.

          limits: The new limits.

          name: The new role name.

          permissions: The new permissions.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._patch(
            f"/v1/admin/roles/{role}",
            body=maybe_transform(
                {
                    "limits": limits,
                    "name": name,
                    "permissions": permissions,
                },
                role_update_params.RoleUpdateParams,
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
        order_by: Literal["id", "name", "created", "updated"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RoleListResponse:
        """
        Get all roles.

        Args:
          limit: The limit of the roles to get.

          offset: The offset of the roles to get.

          order_by: The field to order the roles by.

          order_direction: The direction to order the roles by.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/admin/roles",
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
                    role_list_params.RoleListParams,
                ),
            ),
            cast_to=RoleListResponse,
        )

    def delete(
        self,
        role: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a role.

        Args:
          role: The ID of the role to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/v1/admin/roles/{role}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncRolesResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncRolesResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncRolesResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncRolesResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncRolesResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        name: str,
        limits: Iterable[LimitParam] | Omit = omit,
        permissions: Optional[List[PermissionType]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RoleCreateResponse:
        """
        Create a new role.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/admin/roles",
            body=await async_maybe_transform(
                {
                    "name": name,
                    "limits": limits,
                    "permissions": permissions,
                },
                role_create_params.RoleCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RoleCreateResponse,
        )

    async def retrieve(
        self,
        role: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Role:
        """
        Get a role by id.

        Args:
          role: The ID of the role to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/admin/roles/{role}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Role,
        )

    async def update(
        self,
        role: int,
        *,
        limits: Optional[Iterable[LimitParam]] | Omit = omit,
        name: Optional[str] | Omit = omit,
        permissions: Optional[List[PermissionType]] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update a role.

        Args:
          role: The ID of the role to update.

          limits: The new limits.

          name: The new role name.

          permissions: The new permissions.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._patch(
            f"/v1/admin/roles/{role}",
            body=await async_maybe_transform(
                {
                    "limits": limits,
                    "name": name,
                    "permissions": permissions,
                },
                role_update_params.RoleUpdateParams,
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
        order_by: Literal["id", "name", "created", "updated"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> RoleListResponse:
        """
        Get all roles.

        Args:
          limit: The limit of the roles to get.

          offset: The offset of the roles to get.

          order_by: The field to order the roles by.

          order_direction: The direction to order the roles by.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/admin/roles",
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
                    role_list_params.RoleListParams,
                ),
            ),
            cast_to=RoleListResponse,
        )

    async def delete(
        self,
        role: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a role.

        Args:
          role: The ID of the role to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/v1/admin/roles/{role}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class RolesResourceWithRawResponse:
    def __init__(self, roles: RolesResource) -> None:
        self._roles = roles

        self.create = to_raw_response_wrapper(
            roles.create,
        )
        self.retrieve = to_raw_response_wrapper(
            roles.retrieve,
        )
        self.update = to_raw_response_wrapper(
            roles.update,
        )
        self.list = to_raw_response_wrapper(
            roles.list,
        )
        self.delete = to_raw_response_wrapper(
            roles.delete,
        )


class AsyncRolesResourceWithRawResponse:
    def __init__(self, roles: AsyncRolesResource) -> None:
        self._roles = roles

        self.create = async_to_raw_response_wrapper(
            roles.create,
        )
        self.retrieve = async_to_raw_response_wrapper(
            roles.retrieve,
        )
        self.update = async_to_raw_response_wrapper(
            roles.update,
        )
        self.list = async_to_raw_response_wrapper(
            roles.list,
        )
        self.delete = async_to_raw_response_wrapper(
            roles.delete,
        )


class RolesResourceWithStreamingResponse:
    def __init__(self, roles: RolesResource) -> None:
        self._roles = roles

        self.create = to_streamed_response_wrapper(
            roles.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            roles.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            roles.update,
        )
        self.list = to_streamed_response_wrapper(
            roles.list,
        )
        self.delete = to_streamed_response_wrapper(
            roles.delete,
        )


class AsyncRolesResourceWithStreamingResponse:
    def __init__(self, roles: AsyncRolesResource) -> None:
        self._roles = roles

        self.create = async_to_streamed_response_wrapper(
            roles.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            roles.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            roles.update,
        )
        self.list = async_to_streamed_response_wrapper(
            roles.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            roles.delete,
        )
