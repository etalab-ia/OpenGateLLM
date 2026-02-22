# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestFiles:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_create(self, client: AlbertAPI) -> None:
        file = client.files.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        )
        assert_matches_type(object, file, path=["response"])

    @parametrize
    def test_method_create_with_all_params(self, client: AlbertAPI) -> None:
        file = client.files.create(
            file=b"raw file contents",
            request={
                "collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
                "chunker": {
                    "args": {
                        "chunk_min_size": 0,
                        "chunk_overlap": 0,
                        "chunk_size": 0,
                        "is_separator_regex": True,
                        "length_function": "len",
                        "separators": ["string"],
                    },
                    "name": "LangchainRecursiveCharacterTextSplitter",
                },
            },
        )
        assert_matches_type(object, file, path=["response"])

    @parametrize
    def test_raw_response_create(self, client: AlbertAPI) -> None:
        response = client.files.with_raw_response.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        file = response.parse()
        assert_matches_type(object, file, path=["response"])

    @parametrize
    def test_streaming_response_create(self, client: AlbertAPI) -> None:
        with client.files.with_streaming_response.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            file = response.parse()
            assert_matches_type(object, file, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncFiles:
    parametrize = pytest.mark.parametrize("async_client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    async def test_method_create(self, async_client: AsyncAlbertAPI) -> None:
        file = await async_client.files.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        )
        assert_matches_type(object, file, path=["response"])

    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncAlbertAPI) -> None:
        file = await async_client.files.create(
            file=b"raw file contents",
            request={
                "collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
                "chunker": {
                    "args": {
                        "chunk_min_size": 0,
                        "chunk_overlap": 0,
                        "chunk_size": 0,
                        "is_separator_regex": True,
                        "length_function": "len",
                        "separators": ["string"],
                    },
                    "name": "LangchainRecursiveCharacterTextSplitter",
                },
            },
        )
        assert_matches_type(object, file, path=["response"])

    @parametrize
    async def test_raw_response_create(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.files.with_raw_response.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        file = await response.parse()
        assert_matches_type(object, file, path=["response"])

    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.files.with_streaming_response.create(
            file=b"raw file contents",
            request={"collection": "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e"},
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            file = await response.parse()
            assert_matches_type(object, file, path=["response"])

        assert cast(Any, response.is_closed) is True
