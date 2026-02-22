# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types.admin import (
    Provider,
    ProviderListResponse,
    ProviderCreateResponse,
)

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestProviders:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create(self, client: Opengatellm) -> None:
        provider = client.admin.providers.create(
            model_name="model_name",
            router=0,
            type="albert",
        )
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create_with_all_params(self, client: Opengatellm) -> None:
        provider = client.admin.providers.create(
            model_name="model_name",
            router=0,
            type="albert",
            key="x",
            model_active_params=0,
            model_hosting_zone="ABW",
            model_total_params=0,
            qos_limit=0,
            qos_metric="ttft",
            api_timeout=0,
            url="x",
        )
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_create(self, client: Opengatellm) -> None:
        response = client.admin.providers.with_raw_response.create(
            model_name="model_name",
            router=0,
            type="albert",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = response.parse()
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_create(self, client: Opengatellm) -> None:
        with client.admin.providers.with_streaming_response.create(
            model_name="model_name",
            router=0,
            type="albert",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = response.parse()
            assert_matches_type(ProviderCreateResponse, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_retrieve(self, client: Opengatellm) -> None:
        provider = client.admin.providers.retrieve(
            0,
        )
        assert_matches_type(Provider, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_retrieve(self, client: Opengatellm) -> None:
        response = client.admin.providers.with_raw_response.retrieve(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = response.parse()
        assert_matches_type(Provider, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_retrieve(self, client: Opengatellm) -> None:
        with client.admin.providers.with_streaming_response.retrieve(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = response.parse()
            assert_matches_type(Provider, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update(self, client: Opengatellm) -> None:
        provider = client.admin.providers.update(
            provider=0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update_with_all_params(self, client: Opengatellm) -> None:
        provider = client.admin.providers.update(
            provider=0,
            model_active_params=0,
            model_hosting_zone="ABW",
            model_total_params=0,
            qos_limit=0,
            qos_metric="ttft",
            router=0,
            api_timeout=0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_update(self, client: Opengatellm) -> None:
        response = client.admin.providers.with_raw_response.update(
            provider=0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = response.parse()
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_update(self, client: Opengatellm) -> None:
        with client.admin.providers.with_streaming_response.update(
            provider=0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = response.parse()
            assert provider is None

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list(self, client: Opengatellm) -> None:
        provider = client.admin.providers.list()
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list_with_all_params(self, client: Opengatellm) -> None:
        provider = client.admin.providers.list(
            limit=1,
            offset=0,
            order_by="id",
            order_direction="asc",
            router=0,
        )
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_list(self, client: Opengatellm) -> None:
        response = client.admin.providers.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = response.parse()
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_list(self, client: Opengatellm) -> None:
        with client.admin.providers.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = response.parse()
            assert_matches_type(ProviderListResponse, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_delete(self, client: Opengatellm) -> None:
        provider = client.admin.providers.delete(
            0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_delete(self, client: Opengatellm) -> None:
        response = client.admin.providers.with_raw_response.delete(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = response.parse()
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_delete(self, client: Opengatellm) -> None:
        with client.admin.providers.with_streaming_response.delete(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = response.parse()
            assert provider is None

        assert cast(Any, response.is_closed) is True


class TestAsyncProviders:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.create(
            model_name="model_name",
            router=0,
            type="albert",
        )
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.create(
            model_name="model_name",
            router=0,
            type="albert",
            key="x",
            model_active_params=0,
            model_hosting_zone="ABW",
            model_total_params=0,
            qos_limit=0,
            qos_metric="ttft",
            api_timeout=0,
            url="x",
        )
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_create(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.providers.with_raw_response.create(
            model_name="model_name",
            router=0,
            type="albert",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = await response.parse()
        assert_matches_type(ProviderCreateResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.providers.with_streaming_response.create(
            model_name="model_name",
            router=0,
            type="albert",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = await response.parse()
            assert_matches_type(ProviderCreateResponse, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_retrieve(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.retrieve(
            0,
        )
        assert_matches_type(Provider, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.providers.with_raw_response.retrieve(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = await response.parse()
        assert_matches_type(Provider, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.providers.with_streaming_response.retrieve(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = await response.parse()
            assert_matches_type(Provider, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.update(
            provider=0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.update(
            provider=0,
            model_active_params=0,
            model_hosting_zone="ABW",
            model_total_params=0,
            qos_limit=0,
            qos_metric="ttft",
            router=0,
            api_timeout=0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_update(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.providers.with_raw_response.update(
            provider=0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = await response.parse()
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_update(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.providers.with_streaming_response.update(
            provider=0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = await response.parse()
            assert provider is None

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.list()
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.list(
            limit=1,
            offset=0,
            order_by="id",
            order_direction="asc",
            router=0,
        )
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_list(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.providers.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = await response.parse()
        assert_matches_type(ProviderListResponse, provider, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_list(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.providers.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = await response.parse()
            assert_matches_type(ProviderListResponse, provider, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_delete(self, async_client: AsyncOpengatellm) -> None:
        provider = await async_client.admin.providers.delete(
            0,
        )
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_delete(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.providers.with_raw_response.delete(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        provider = await response.parse()
        assert provider is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_delete(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.providers.with_streaming_response.delete(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            provider = await response.parse()
            assert provider is None

        assert cast(Any, response.is_closed) is True
