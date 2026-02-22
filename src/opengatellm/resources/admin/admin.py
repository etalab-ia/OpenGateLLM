# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from .roles import (
    RolesResource,
    AsyncRolesResource,
    RolesResourceWithRawResponse,
    AsyncRolesResourceWithRawResponse,
    RolesResourceWithStreamingResponse,
    AsyncRolesResourceWithStreamingResponse,
)
from .users import (
    UsersResource,
    AsyncUsersResource,
    UsersResourceWithRawResponse,
    AsyncUsersResourceWithRawResponse,
    UsersResourceWithStreamingResponse,
    AsyncUsersResourceWithStreamingResponse,
)
from .tokens import (
    TokensResource,
    AsyncTokensResource,
    TokensResourceWithRawResponse,
    AsyncTokensResourceWithRawResponse,
    TokensResourceWithStreamingResponse,
    AsyncTokensResourceWithStreamingResponse,
)
from .routers import (
    RoutersResource,
    AsyncRoutersResource,
    RoutersResourceWithRawResponse,
    AsyncRoutersResourceWithRawResponse,
    RoutersResourceWithStreamingResponse,
    AsyncRoutersResourceWithStreamingResponse,
)
from ..._compat import cached_property
from .providers import (
    ProvidersResource,
    AsyncProvidersResource,
    ProvidersResourceWithRawResponse,
    AsyncProvidersResourceWithRawResponse,
    ProvidersResourceWithStreamingResponse,
    AsyncProvidersResourceWithStreamingResponse,
)
from ..._resource import SyncAPIResource, AsyncAPIResource
from .organizations import (
    OrganizationsResource,
    AsyncOrganizationsResource,
    OrganizationsResourceWithRawResponse,
    AsyncOrganizationsResourceWithRawResponse,
    OrganizationsResourceWithStreamingResponse,
    AsyncOrganizationsResourceWithStreamingResponse,
)

__all__ = ["AdminResource", "AsyncAdminResource"]


class AdminResource(SyncAPIResource):
    @cached_property
    def organizations(self) -> OrganizationsResource:
        return OrganizationsResource(self._client)

    @cached_property
    def providers(self) -> ProvidersResource:
        return ProvidersResource(self._client)

    @cached_property
    def roles(self) -> RolesResource:
        return RolesResource(self._client)

    @cached_property
    def routers(self) -> RoutersResource:
        return RoutersResource(self._client)

    @cached_property
    def tokens(self) -> TokensResource:
        return TokensResource(self._client)

    @cached_property
    def users(self) -> UsersResource:
        return UsersResource(self._client)

    @cached_property
    def with_raw_response(self) -> AdminResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AdminResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AdminResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AdminResourceWithStreamingResponse(self)


class AsyncAdminResource(AsyncAPIResource):
    @cached_property
    def organizations(self) -> AsyncOrganizationsResource:
        return AsyncOrganizationsResource(self._client)

    @cached_property
    def providers(self) -> AsyncProvidersResource:
        return AsyncProvidersResource(self._client)

    @cached_property
    def roles(self) -> AsyncRolesResource:
        return AsyncRolesResource(self._client)

    @cached_property
    def routers(self) -> AsyncRoutersResource:
        return AsyncRoutersResource(self._client)

    @cached_property
    def tokens(self) -> AsyncTokensResource:
        return AsyncTokensResource(self._client)

    @cached_property
    def users(self) -> AsyncUsersResource:
        return AsyncUsersResource(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncAdminResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncAdminResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncAdminResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncAdminResourceWithStreamingResponse(self)


class AdminResourceWithRawResponse:
    def __init__(self, admin: AdminResource) -> None:
        self._admin = admin

    @cached_property
    def organizations(self) -> OrganizationsResourceWithRawResponse:
        return OrganizationsResourceWithRawResponse(self._admin.organizations)

    @cached_property
    def providers(self) -> ProvidersResourceWithRawResponse:
        return ProvidersResourceWithRawResponse(self._admin.providers)

    @cached_property
    def roles(self) -> RolesResourceWithRawResponse:
        return RolesResourceWithRawResponse(self._admin.roles)

    @cached_property
    def routers(self) -> RoutersResourceWithRawResponse:
        return RoutersResourceWithRawResponse(self._admin.routers)

    @cached_property
    def tokens(self) -> TokensResourceWithRawResponse:
        return TokensResourceWithRawResponse(self._admin.tokens)

    @cached_property
    def users(self) -> UsersResourceWithRawResponse:
        return UsersResourceWithRawResponse(self._admin.users)


class AsyncAdminResourceWithRawResponse:
    def __init__(self, admin: AsyncAdminResource) -> None:
        self._admin = admin

    @cached_property
    def organizations(self) -> AsyncOrganizationsResourceWithRawResponse:
        return AsyncOrganizationsResourceWithRawResponse(self._admin.organizations)

    @cached_property
    def providers(self) -> AsyncProvidersResourceWithRawResponse:
        return AsyncProvidersResourceWithRawResponse(self._admin.providers)

    @cached_property
    def roles(self) -> AsyncRolesResourceWithRawResponse:
        return AsyncRolesResourceWithRawResponse(self._admin.roles)

    @cached_property
    def routers(self) -> AsyncRoutersResourceWithRawResponse:
        return AsyncRoutersResourceWithRawResponse(self._admin.routers)

    @cached_property
    def tokens(self) -> AsyncTokensResourceWithRawResponse:
        return AsyncTokensResourceWithRawResponse(self._admin.tokens)

    @cached_property
    def users(self) -> AsyncUsersResourceWithRawResponse:
        return AsyncUsersResourceWithRawResponse(self._admin.users)


class AdminResourceWithStreamingResponse:
    def __init__(self, admin: AdminResource) -> None:
        self._admin = admin

    @cached_property
    def organizations(self) -> OrganizationsResourceWithStreamingResponse:
        return OrganizationsResourceWithStreamingResponse(self._admin.organizations)

    @cached_property
    def providers(self) -> ProvidersResourceWithStreamingResponse:
        return ProvidersResourceWithStreamingResponse(self._admin.providers)

    @cached_property
    def roles(self) -> RolesResourceWithStreamingResponse:
        return RolesResourceWithStreamingResponse(self._admin.roles)

    @cached_property
    def routers(self) -> RoutersResourceWithStreamingResponse:
        return RoutersResourceWithStreamingResponse(self._admin.routers)

    @cached_property
    def tokens(self) -> TokensResourceWithStreamingResponse:
        return TokensResourceWithStreamingResponse(self._admin.tokens)

    @cached_property
    def users(self) -> UsersResourceWithStreamingResponse:
        return UsersResourceWithStreamingResponse(self._admin.users)


class AsyncAdminResourceWithStreamingResponse:
    def __init__(self, admin: AsyncAdminResource) -> None:
        self._admin = admin

    @cached_property
    def organizations(self) -> AsyncOrganizationsResourceWithStreamingResponse:
        return AsyncOrganizationsResourceWithStreamingResponse(self._admin.organizations)

    @cached_property
    def providers(self) -> AsyncProvidersResourceWithStreamingResponse:
        return AsyncProvidersResourceWithStreamingResponse(self._admin.providers)

    @cached_property
    def roles(self) -> AsyncRolesResourceWithStreamingResponse:
        return AsyncRolesResourceWithStreamingResponse(self._admin.roles)

    @cached_property
    def routers(self) -> AsyncRoutersResourceWithStreamingResponse:
        return AsyncRoutersResourceWithStreamingResponse(self._admin.routers)

    @cached_property
    def tokens(self) -> AsyncTokensResourceWithStreamingResponse:
        return AsyncTokensResourceWithStreamingResponse(self._admin.tokens)

    @cached_property
    def users(self) -> AsyncUsersResourceWithStreamingResponse:
        return AsyncUsersResourceWithStreamingResponse(self._admin.users)
