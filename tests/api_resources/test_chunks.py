# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import Chunk, ChunkListResponse

# pyright: reportDeprecated=false

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestChunks:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_retrieve(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = client.chunks.retrieve(
                chunk=0,
                document=0,
            )

        assert_matches_type(Chunk, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_retrieve(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = client.chunks.with_raw_response.retrieve(
                chunk=0,
                document=0,
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chunk = response.parse()
        assert_matches_type(Chunk, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_retrieve(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            with client.chunks.with_streaming_response.retrieve(
                chunk=0,
                document=0,
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                chunk = response.parse()
                assert_matches_type(Chunk, chunk, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = client.chunks.list(
                document=0,
            )

        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_list_with_all_params(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = client.chunks.list(
                document=0,
                limit=1,
                offset=0,
            )

        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_list(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = client.chunks.with_raw_response.list(
                document=0,
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chunk = response.parse()
        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_list(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            with client.chunks.with_streaming_response.list(
                document=0,
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                chunk = response.parse()
                assert_matches_type(ChunkListResponse, chunk, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncChunks:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_retrieve(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = await async_client.chunks.retrieve(
                chunk=0,
                document=0,
            )

        assert_matches_type(Chunk, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = await async_client.chunks.with_raw_response.retrieve(
                chunk=0,
                document=0,
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chunk = await response.parse()
        assert_matches_type(Chunk, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_retrieve(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            async with async_client.chunks.with_streaming_response.retrieve(
                chunk=0,
                document=0,
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                chunk = await response.parse()
                assert_matches_type(Chunk, chunk, path=["response"])

        assert cast(Any, response.is_closed) is True

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = await async_client.chunks.list(
                document=0,
            )

        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_list_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            chunk = await async_client.chunks.list(
                document=0,
                limit=1,
                offset=0,
            )

        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_list(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = await async_client.chunks.with_raw_response.list(
                document=0,
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chunk = await response.parse()
        assert_matches_type(ChunkListResponse, chunk, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_list(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            async with async_client.chunks.with_streaming_response.list(
                document=0,
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                chunk = await response.parse()
                assert_matches_type(ChunkListResponse, chunk, path=["response"])

        assert cast(Any, response.is_closed) is True
