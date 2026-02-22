# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestHealth:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_check(self, client: AlbertAPI) -> None:
        health = client.health.check()
        assert_matches_type(object, health, path=["response"])

    @parametrize
    def test_raw_response_check(self, client: AlbertAPI) -> None:
        response = client.health.with_raw_response.check()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        health = response.parse()
        assert_matches_type(object, health, path=["response"])

    @parametrize
    def test_streaming_response_check(self, client: AlbertAPI) -> None:
        with client.health.with_streaming_response.check() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            health = response.parse()
            assert_matches_type(object, health, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncHealth:
    parametrize = pytest.mark.parametrize("async_client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    async def test_method_check(self, async_client: AsyncAlbertAPI) -> None:
        health = await async_client.health.check()
        assert_matches_type(object, health, path=["response"])

    @parametrize
    async def test_raw_response_check(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.health.with_raw_response.check()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        health = await response.parse()
        assert_matches_type(object, health, path=["response"])

    @parametrize
    async def test_streaming_response_check(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.health.with_streaming_response.check() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            health = await response.parse()
            assert_matches_type(object, health, path=["response"])

        assert cast(Any, response.is_closed) is True
