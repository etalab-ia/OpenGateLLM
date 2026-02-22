# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import RerankCreateResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestRerank:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create(self, client: Opengatellm) -> None:
        rerank = client.rerank.create(
            model="x",
        )
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create_with_all_params(self, client: Opengatellm) -> None:
        rerank = client.rerank.create(
            model="x",
            documents=["x"],
            input=["x"],
            prompt="x",
            query="x",
            top_n=1,
        )
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_create(self, client: Opengatellm) -> None:
        response = client.rerank.with_raw_response.create(
            model="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        rerank = response.parse()
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_create(self, client: Opengatellm) -> None:
        with client.rerank.with_streaming_response.create(
            model="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            rerank = response.parse()
            assert_matches_type(RerankCreateResponse, rerank, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncRerank:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create(self, async_client: AsyncOpengatellm) -> None:
        rerank = await async_client.rerank.create(
            model="x",
        )
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        rerank = await async_client.rerank.create(
            model="x",
            documents=["x"],
            input=["x"],
            prompt="x",
            query="x",
            top_n=1,
        )
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_create(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.rerank.with_raw_response.create(
            model="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        rerank = await response.parse()
        assert_matches_type(RerankCreateResponse, rerank, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.rerank.with_streaming_response.create(
            model="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            rerank = await response.parse()
            assert_matches_type(RerankCreateResponse, rerank, path=["response"])

        assert cast(Any, response.is_closed) is True
