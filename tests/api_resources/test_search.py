# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type
from albert_api.types import Searches

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestSearch:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_execute(self, client: AlbertAPI) -> None:
        search = client.search.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        )
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    def test_method_execute_with_all_params(self, client: AlbertAPI) -> None:
        search = client.search.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
            score_threshold=0,
        )
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    def test_raw_response_execute(self, client: AlbertAPI) -> None:
        response = client.search.with_raw_response.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        search = response.parse()
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    def test_streaming_response_execute(self, client: AlbertAPI) -> None:
        with client.search.with_streaming_response.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            search = response.parse()
            assert_matches_type(Searches, search, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncSearch:
    parametrize = pytest.mark.parametrize("async_client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    async def test_method_execute(self, async_client: AsyncAlbertAPI) -> None:
        search = await async_client.search.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        )
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    async def test_method_execute_with_all_params(self, async_client: AsyncAlbertAPI) -> None:
        search = await async_client.search.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
            score_threshold=0,
        )
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    async def test_raw_response_execute(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.search.with_raw_response.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        search = await response.parse()
        assert_matches_type(Searches, search, path=["response"])

    @parametrize
    async def test_streaming_response_execute(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.search.with_streaming_response.execute(
            collections=["182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"],
            k=1,
            prompt="prompt",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            search = await response.parse()
            assert_matches_type(Searches, search, path=["response"])

        assert cast(Any, response.is_closed) is True
