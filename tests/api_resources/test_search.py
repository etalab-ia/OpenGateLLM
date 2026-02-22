# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import SearchPerformResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestSearch:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_perform(self, client: Opengatellm) -> None:
        search = client.search.perform(
            collections=[0],
            prompt="x",
        )
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_perform_with_all_params(self, client: Opengatellm) -> None:
        search = client.search.perform(
            collections=[0],
            prompt="x",
            limit=1,
            method="hybrid",
            offset=0,
            rff_k=0,
            score_threshold=0,
        )
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_perform(self, client: Opengatellm) -> None:
        response = client.search.with_raw_response.perform(
            collections=[0],
            prompt="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        search = response.parse()
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_perform(self, client: Opengatellm) -> None:
        with client.search.with_streaming_response.perform(
            collections=[0],
            prompt="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            search = response.parse()
            assert_matches_type(SearchPerformResponse, search, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncSearch:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_perform(self, async_client: AsyncOpengatellm) -> None:
        search = await async_client.search.perform(
            collections=[0],
            prompt="x",
        )
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_perform_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        search = await async_client.search.perform(
            collections=[0],
            prompt="x",
            limit=1,
            method="hybrid",
            offset=0,
            rff_k=0,
            score_threshold=0,
        )
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_perform(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.search.with_raw_response.perform(
            collections=[0],
            prompt="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        search = await response.parse()
        assert_matches_type(SearchPerformResponse, search, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_perform(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.search.with_streaming_response.perform(
            collections=[0],
            prompt="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            search = await response.parse()
            assert_matches_type(SearchPerformResponse, search, path=["response"])

        assert cast(Any, response.is_closed) is True
