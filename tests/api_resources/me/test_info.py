# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types.me import InfoRetrieveResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestInfo:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_retrieve(self, client: Opengatellm) -> None:
        info = client.me.info.retrieve()
        assert_matches_type(InfoRetrieveResponse, info, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_retrieve(self, client: Opengatellm) -> None:
        response = client.me.info.with_raw_response.retrieve()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        info = response.parse()
        assert_matches_type(InfoRetrieveResponse, info, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_retrieve(self, client: Opengatellm) -> None:
        with client.me.info.with_streaming_response.retrieve() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            info = response.parse()
            assert_matches_type(InfoRetrieveResponse, info, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update(self, client: Opengatellm) -> None:
        info = client.me.info.update()
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_update_with_all_params(self, client: Opengatellm) -> None:
        info = client.me.info.update(
            current_password="current_password",
            email="email",
            name="name",
            password="password",
        )
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_update(self, client: Opengatellm) -> None:
        response = client.me.info.with_raw_response.update()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        info = response.parse()
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_update(self, client: Opengatellm) -> None:
        with client.me.info.with_streaming_response.update() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            info = response.parse()
            assert info is None

        assert cast(Any, response.is_closed) is True


class TestAsyncInfo:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_retrieve(self, async_client: AsyncOpengatellm) -> None:
        info = await async_client.me.info.retrieve()
        assert_matches_type(InfoRetrieveResponse, info, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.me.info.with_raw_response.retrieve()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        info = await response.parse()
        assert_matches_type(InfoRetrieveResponse, info, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.me.info.with_streaming_response.retrieve() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            info = await response.parse()
            assert_matches_type(InfoRetrieveResponse, info, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update(self, async_client: AsyncOpengatellm) -> None:
        info = await async_client.me.info.update()
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_update_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        info = await async_client.me.info.update(
            current_password="current_password",
            email="email",
            name="name",
            password="password",
        )
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_update(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.me.info.with_raw_response.update()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        info = await response.parse()
        assert info is None

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_update(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.me.info.with_streaming_response.update() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            info = await response.parse()
            assert info is None

        assert cast(Any, response.is_closed) is True
