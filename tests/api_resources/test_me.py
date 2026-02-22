# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import MeGetUsageResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestMe:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_get_usage(self, client: Opengatellm) -> None:
        me = client.me.get_usage()
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_get_usage_with_all_params(self, client: Opengatellm) -> None:
        me = client.me.get_usage(
            end_time=0,
            endpoint="/v1/audio/transcriptions",
            limit=1,
            offset=0,
            start_time=0,
        )
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_get_usage(self, client: Opengatellm) -> None:
        response = client.me.with_raw_response.get_usage()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        me = response.parse()
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_get_usage(self, client: Opengatellm) -> None:
        with client.me.with_streaming_response.get_usage() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            me = response.parse()
            assert_matches_type(MeGetUsageResponse, me, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncMe:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_get_usage(self, async_client: AsyncOpengatellm) -> None:
        me = await async_client.me.get_usage()
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_get_usage_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        me = await async_client.me.get_usage(
            end_time=0,
            endpoint="/v1/audio/transcriptions",
            limit=1,
            offset=0,
            start_time=0,
        )
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_get_usage(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.me.with_raw_response.get_usage()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        me = await response.parse()
        assert_matches_type(MeGetUsageResponse, me, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_get_usage(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.me.with_streaming_response.get_usage() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            me = await response.parse()
            assert_matches_type(MeGetUsageResponse, me, path=["response"])

        assert cast(Any, response.is_closed) is True
