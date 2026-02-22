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
from ...types.admin import (
    Metric,
    ProviderType,
    ProviderCarbonFootprintZone,
    provider_list_params,
    provider_create_params,
    provider_update_params,
)
from ..._base_client import make_request_options
from ...types.admin.metric import Metric
from ...types.admin.provider import Provider
from ...types.admin.provider_type import ProviderType
from ...types.admin.provider_list_response import ProviderListResponse
from ...types.admin.provider_create_response import ProviderCreateResponse
from ...types.admin.provider_carbon_footprint_zone import ProviderCarbonFootprintZone

__all__ = ["ProvidersResource", "AsyncProvidersResource"]


class ProvidersResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ProvidersResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return ProvidersResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ProvidersResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return ProvidersResourceWithStreamingResponse(self)

    def create(
        self,
        *,
        model_name: str,
        router: int,
        type: ProviderType,
        key: Optional[str] | Omit = omit,
        model_active_params: int | Omit = omit,
        model_hosting_zone: ProviderCarbonFootprintZone | Omit = omit,
        model_total_params: int | Omit = omit,
        qos_limit: Optional[float] | Omit = omit,
        qos_metric: Optional[Metric] | Omit = omit,
        api_timeout: int | Omit = omit,
        url: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ProviderCreateResponse:
        """
        Create a model provider.

        Args:
          model_name: Model name from the model provider.

          router: ID of the model to create the provider for (router ID, eg. 123).

          type: Model provider type.

          key: Model provider API key.

          model_active_params: Active params of the model in billions of parameters for carbon footprint
              computation. For more information, see https://ecologits.ai

          model_hosting_zone: Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
              `FRA` for France, `USA` for United States). This determines the electricity mix
              used for carbon intensity calculations. For more information, see
              https://ecologits.ai

          model_total_params: Total params of the model in billions of parameters for carbon footprint
              computation. For more information, see https://ecologits.ai

          qos_limit: The value to use for the quality of service. Depends of the metric, the value
              can be a percentile, a threshold, etc.

          qos_metric: The metric to use for the quality of service policy. If not provided, no QoS
              policy is applied.

          api_timeout: Timeout for the model provider requests, after user receive an 503 error (model
              is too busy).

          url: Model provider API url. The url must only contain the domain name (without `/v1`
              suffix for example). Depends of the model provider type, the url can be optional
              (Albert, OpenAI).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/v1/admin/providers",
            body=maybe_transform(
                {
                    "model_name": model_name,
                    "router": router,
                    "type": type,
                    "key": key,
                    "model_active_params": model_active_params,
                    "model_hosting_zone": model_hosting_zone,
                    "model_total_params": model_total_params,
                    "qos_limit": qos_limit,
                    "qos_metric": qos_metric,
                    "api_timeout": api_timeout,
                    "url": url,
                },
                provider_create_params.ProviderCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ProviderCreateResponse,
        )

    def retrieve(
        self,
        provider: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Provider:
        """
        Get a model provider by router and provider IDs.

        Args:
          provider: The ID of the provider to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            f"/v1/admin/providers/{provider}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Provider,
        )

    def update(
        self,
        provider: int,
        *,
        model_active_params: Optional[int] | Omit = omit,
        model_hosting_zone: Optional[ProviderCarbonFootprintZone] | Omit = omit,
        model_total_params: Optional[int] | Omit = omit,
        qos_limit: Optional[float] | Omit = omit,
        qos_metric: Optional[Metric] | Omit = omit,
        router: Optional[int] | Omit = omit,
        api_timeout: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update a model provider.

        Args:
          provider: The ID of the provider to update.

          model_active_params: Active params of the model in billions of parameters for carbon footprint
              computation. If not provided, the total params will be used if provided, else
              carbon footprint will not be computed. For more information, see
              https://ecologits.ai

          model_hosting_zone: Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
              `FRA` for France, `USA` for United States). This determines the electricity mix
              used for carbon intensity calculations. For more information, see
              https://ecologits.ai

          model_total_params: Total params of the model in billions of parameters for carbon footprint
              computation. If not provided, the active params will be used if provided, else
              carbon footprint will not be computed. For more information, see
              https://ecologits.ai

          qos_limit: The value to use for the quality of service. Depends of the metric, the value
              can be a percentile, a threshold, etc.

          qos_metric: The metric to use for the quality of service policy. If not provided, no QoS
              policy is applied.

          router: The ID of the new router to assign to the provider.

          api_timeout: Timeout for the model provider requests, after user receive an 500 error (model
              is too busy).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._patch(
            f"/v1/admin/providers/{provider}",
            body=maybe_transform(
                {
                    "model_active_params": model_active_params,
                    "model_hosting_zone": model_hosting_zone,
                    "model_total_params": model_total_params,
                    "qos_limit": qos_limit,
                    "qos_metric": qos_metric,
                    "router": router,
                    "api_timeout": api_timeout,
                },
                provider_update_params.ProviderUpdateParams,
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
        order_by: Literal["id", "model_name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        router: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ProviderListResponse:
        """
        Get all model providers for a router.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          router: Filter providers by router ID.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get(
            "/v1/admin/providers",
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
                        "router": router,
                    },
                    provider_list_params.ProviderListParams,
                ),
            ),
            cast_to=ProviderListResponse,
        )

    def delete(
        self,
        provider: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a router provider.

        Args:
          provider: The ID of the provider to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/v1/admin/providers/{provider}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncProvidersResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncProvidersResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#accessing-raw-response-data-eg-headers
        """
        return AsyncProvidersResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncProvidersResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/stainless-sdks/opengatellm-python#with_streaming_response
        """
        return AsyncProvidersResourceWithStreamingResponse(self)

    async def create(
        self,
        *,
        model_name: str,
        router: int,
        type: ProviderType,
        key: Optional[str] | Omit = omit,
        model_active_params: int | Omit = omit,
        model_hosting_zone: ProviderCarbonFootprintZone | Omit = omit,
        model_total_params: int | Omit = omit,
        qos_limit: Optional[float] | Omit = omit,
        qos_metric: Optional[Metric] | Omit = omit,
        api_timeout: int | Omit = omit,
        url: Optional[str] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ProviderCreateResponse:
        """
        Create a model provider.

        Args:
          model_name: Model name from the model provider.

          router: ID of the model to create the provider for (router ID, eg. 123).

          type: Model provider type.

          key: Model provider API key.

          model_active_params: Active params of the model in billions of parameters for carbon footprint
              computation. For more information, see https://ecologits.ai

          model_hosting_zone: Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
              `FRA` for France, `USA` for United States). This determines the electricity mix
              used for carbon intensity calculations. For more information, see
              https://ecologits.ai

          model_total_params: Total params of the model in billions of parameters for carbon footprint
              computation. For more information, see https://ecologits.ai

          qos_limit: The value to use for the quality of service. Depends of the metric, the value
              can be a percentile, a threshold, etc.

          qos_metric: The metric to use for the quality of service policy. If not provided, no QoS
              policy is applied.

          api_timeout: Timeout for the model provider requests, after user receive an 503 error (model
              is too busy).

          url: Model provider API url. The url must only contain the domain name (without `/v1`
              suffix for example). Depends of the model provider type, the url can be optional
              (Albert, OpenAI).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/v1/admin/providers",
            body=await async_maybe_transform(
                {
                    "model_name": model_name,
                    "router": router,
                    "type": type,
                    "key": key,
                    "model_active_params": model_active_params,
                    "model_hosting_zone": model_hosting_zone,
                    "model_total_params": model_total_params,
                    "qos_limit": qos_limit,
                    "qos_metric": qos_metric,
                    "api_timeout": api_timeout,
                    "url": url,
                },
                provider_create_params.ProviderCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ProviderCreateResponse,
        )

    async def retrieve(
        self,
        provider: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> Provider:
        """
        Get a model provider by router and provider IDs.

        Args:
          provider: The ID of the provider to get.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            f"/v1/admin/providers/{provider}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Provider,
        )

    async def update(
        self,
        provider: int,
        *,
        model_active_params: Optional[int] | Omit = omit,
        model_hosting_zone: Optional[ProviderCarbonFootprintZone] | Omit = omit,
        model_total_params: Optional[int] | Omit = omit,
        qos_limit: Optional[float] | Omit = omit,
        qos_metric: Optional[Metric] | Omit = omit,
        router: Optional[int] | Omit = omit,
        api_timeout: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Update a model provider.

        Args:
          provider: The ID of the provider to update.

          model_active_params: Active params of the model in billions of parameters for carbon footprint
              computation. If not provided, the total params will be used if provided, else
              carbon footprint will not be computed. For more information, see
              https://ecologits.ai

          model_hosting_zone: Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World,
              `FRA` for France, `USA` for United States). This determines the electricity mix
              used for carbon intensity calculations. For more information, see
              https://ecologits.ai

          model_total_params: Total params of the model in billions of parameters for carbon footprint
              computation. If not provided, the active params will be used if provided, else
              carbon footprint will not be computed. For more information, see
              https://ecologits.ai

          qos_limit: The value to use for the quality of service. Depends of the metric, the value
              can be a percentile, a threshold, etc.

          qos_metric: The metric to use for the quality of service policy. If not provided, no QoS
              policy is applied.

          router: The ID of the new router to assign to the provider.

          api_timeout: Timeout for the model provider requests, after user receive an 500 error (model
              is too busy).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._patch(
            f"/v1/admin/providers/{provider}",
            body=await async_maybe_transform(
                {
                    "model_active_params": model_active_params,
                    "model_hosting_zone": model_hosting_zone,
                    "model_total_params": model_total_params,
                    "qos_limit": qos_limit,
                    "qos_metric": qos_metric,
                    "router": router,
                    "api_timeout": api_timeout,
                },
                provider_update_params.ProviderUpdateParams,
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
        order_by: Literal["id", "model_name", "created"] | Omit = omit,
        order_direction: Literal["asc", "desc"] | Omit = omit,
        router: Optional[int] | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> ProviderListResponse:
        """
        Get all model providers for a router.

        Args:
          limit: The limit of the tokens to get.

          offset: The offset of the tokens to get.

          order_by: The field to order the tokens by.

          order_direction: The direction to order the tokens by.

          router: Filter providers by router ID.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._get(
            "/v1/admin/providers",
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
                        "router": router,
                    },
                    provider_list_params.ProviderListParams,
                ),
            ),
            cast_to=ProviderListResponse,
        )

    async def delete(
        self,
        provider: int,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> None:
        """
        Delete a router provider.

        Args:
          provider: The ID of the provider to delete.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/v1/admin/providers/{provider}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class ProvidersResourceWithRawResponse:
    def __init__(self, providers: ProvidersResource) -> None:
        self._providers = providers

        self.create = to_raw_response_wrapper(
            providers.create,
        )
        self.retrieve = to_raw_response_wrapper(
            providers.retrieve,
        )
        self.update = to_raw_response_wrapper(
            providers.update,
        )
        self.list = to_raw_response_wrapper(
            providers.list,
        )
        self.delete = to_raw_response_wrapper(
            providers.delete,
        )


class AsyncProvidersResourceWithRawResponse:
    def __init__(self, providers: AsyncProvidersResource) -> None:
        self._providers = providers

        self.create = async_to_raw_response_wrapper(
            providers.create,
        )
        self.retrieve = async_to_raw_response_wrapper(
            providers.retrieve,
        )
        self.update = async_to_raw_response_wrapper(
            providers.update,
        )
        self.list = async_to_raw_response_wrapper(
            providers.list,
        )
        self.delete = async_to_raw_response_wrapper(
            providers.delete,
        )


class ProvidersResourceWithStreamingResponse:
    def __init__(self, providers: ProvidersResource) -> None:
        self._providers = providers

        self.create = to_streamed_response_wrapper(
            providers.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            providers.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            providers.update,
        )
        self.list = to_streamed_response_wrapper(
            providers.list,
        )
        self.delete = to_streamed_response_wrapper(
            providers.delete,
        )


class AsyncProvidersResourceWithStreamingResponse:
    def __init__(self, providers: AsyncProvidersResource) -> None:
        self._providers = providers

        self.create = async_to_streamed_response_wrapper(
            providers.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            providers.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            providers.update,
        )
        self.list = async_to_streamed_response_wrapper(
            providers.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            providers.delete,
        )
