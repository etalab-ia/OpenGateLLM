# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import AuthLoginResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestAuth:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_login(self, client: Opengatellm) -> None:
        auth = client.auth.login(
            email="x",
            password="x",
        )
        assert_matches_type(AuthLoginResponse, auth, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_login(self, client: Opengatellm) -> None:
        response = client.auth.with_raw_response.login(
            email="x",
            password="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        auth = response.parse()
        assert_matches_type(AuthLoginResponse, auth, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_login(self, client: Opengatellm) -> None:
        with client.auth.with_streaming_response.login(
            email="x",
            password="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            auth = response.parse()
            assert_matches_type(AuthLoginResponse, auth, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncAuth:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_login(self, async_client: AsyncOpengatellm) -> None:
        auth = await async_client.auth.login(
            email="x",
            password="x",
        )
        assert_matches_type(AuthLoginResponse, auth, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_login(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.auth.with_raw_response.login(
            email="x",
            password="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        auth = await response.parse()
        assert_matches_type(AuthLoginResponse, auth, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_login(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.auth.with_streaming_response.login(
            email="x",
            password="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            auth = await response.parse()
            assert_matches_type(AuthLoginResponse, auth, path=["response"])

        assert cast(Any, response.is_closed) is True
