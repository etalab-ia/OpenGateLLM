# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types.admin import (
    Router,
    RouterListResponse,
    RouterCreateResponse,
)

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestRouters:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create(self, client: Opengatellm) -> None:
        router = client.admin.routers.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        )
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create_with_all_params(self, client: Opengatellm) -> None:
        router = client.admin.routers.create(
            name="model-router-1",
            type="automatic-speech-recognition",
            aliases=["model-alias", "model-alias-2"],
            cost_completion_tokens=0,
            cost_prompt_tokens=0,
            load_balancing_strategy="shuffle",
        )
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_create(self, client: Opengatellm) -> None:
        response = client.admin.routers.with_raw_response.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = response.parse()
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_create(self, client: Opengatellm) -> None:
        with client.admin.routers.with_streaming_response.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = response.parse()
            assert_matches_type(RouterCreateResponse, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_retrieve(self, client: Opengatellm) -> None:
        router = client.admin.routers.retrieve(
            0,
        )
        assert_matches_type(Router, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_retrieve(self, client: Opengatellm) -> None:
        response = client.admin.routers.with_raw_response.retrieve(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = response.parse()
        assert_matches_type(Router, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_retrieve(self, client: Opengatellm) -> None:
        with client.admin.routers.with_streaming_response.retrieve(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = response.parse()
            assert_matches_type(Router, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update(self, client: Opengatellm) -> None:
        router = client.admin.routers.update(
            router=0,
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update_with_all_params(self, client: Opengatellm) -> None:
        router = client.admin.routers.update(
            router=0,
            aliases=["model-alias", "model-alias-2"],
            cost_completion_tokens=0,
            cost_prompt_tokens=0,
            load_balancing_strategy="shuffle",
            name="model-router-1",
            type="automatic-speech-recognition",
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_update(self, client: Opengatellm) -> None:
        response = client.admin.routers.with_raw_response.update(
            router=0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = response.parse()
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_update(self, client: Opengatellm) -> None:
        with client.admin.routers.with_streaming_response.update(
            router=0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = response.parse()
            assert router is None

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list(self, client: Opengatellm) -> None:
        router = client.admin.routers.list()
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list_with_all_params(self, client: Opengatellm) -> None:
        router = client.admin.routers.list(
            limit=1,
            offset=0,
            order_by="id",
            order_direction="asc",
        )
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_list(self, client: Opengatellm) -> None:
        response = client.admin.routers.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = response.parse()
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_list(self, client: Opengatellm) -> None:
        with client.admin.routers.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = response.parse()
            assert_matches_type(RouterListResponse, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_delete(self, client: Opengatellm) -> None:
        router = client.admin.routers.delete(
            0,
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_delete(self, client: Opengatellm) -> None:
        response = client.admin.routers.with_raw_response.delete(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = response.parse()
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_delete(self, client: Opengatellm) -> None:
        with client.admin.routers.with_streaming_response.delete(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = response.parse()
            assert router is None

        assert cast(Any, response.is_closed) is True


class TestAsyncRouters:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        )
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.create(
            name="model-router-1",
            type="automatic-speech-recognition",
            aliases=["model-alias", "model-alias-2"],
            cost_completion_tokens=0,
            cost_prompt_tokens=0,
            load_balancing_strategy="shuffle",
        )
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_create(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.routers.with_raw_response.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = await response.parse()
        assert_matches_type(RouterCreateResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.routers.with_streaming_response.create(
            name="model-router-1",
            type="automatic-speech-recognition",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = await response.parse()
            assert_matches_type(RouterCreateResponse, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_retrieve(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.retrieve(
            0,
        )
        assert_matches_type(Router, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.routers.with_raw_response.retrieve(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = await response.parse()
        assert_matches_type(Router, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.routers.with_streaming_response.retrieve(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = await response.parse()
            assert_matches_type(Router, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.update(
            router=0,
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.update(
            router=0,
            aliases=["model-alias", "model-alias-2"],
            cost_completion_tokens=0,
            cost_prompt_tokens=0,
            load_balancing_strategy="shuffle",
            name="model-router-1",
            type="automatic-speech-recognition",
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_update(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.routers.with_raw_response.update(
            router=0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = await response.parse()
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_update(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.routers.with_streaming_response.update(
            router=0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = await response.parse()
            assert router is None

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.list()
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.list(
            limit=1,
            offset=0,
            order_by="id",
            order_direction="asc",
        )
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_list(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.routers.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = await response.parse()
        assert_matches_type(RouterListResponse, router, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_list(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.routers.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = await response.parse()
            assert_matches_type(RouterListResponse, router, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_delete(self, async_client: AsyncOpengatellm) -> None:
        router = await async_client.admin.routers.delete(
            0,
        )
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_delete(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.admin.routers.with_raw_response.delete(
            0,
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        router = await response.parse()
        assert router is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_delete(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.admin.routers.with_streaming_response.delete(
            0,
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            router = await response.parse()
            assert router is None

        assert cast(Any, response.is_closed) is True
