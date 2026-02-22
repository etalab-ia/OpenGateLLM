# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type
from albert_api.types import CollectionListResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestCollections:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_create(self, client: AlbertAPI) -> None:
        collection = client.collections.create(
            model="model",
            name="x",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    def test_method_create_with_all_params(self, client: AlbertAPI) -> None:
        collection = client.collections.create(
            model="model",
            name="x",
            type="public",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    def test_raw_response_create(self, client: AlbertAPI) -> None:
        response = client.collections.with_raw_response.create(
            model="model",
            name="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = response.parse()
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    def test_streaming_response_create(self, client: AlbertAPI) -> None:
        with client.collections.with_streaming_response.create(
            model="model",
            name="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = response.parse()
            assert_matches_type(object, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    def test_method_list(self, client: AlbertAPI) -> None:
        collection = client.collections.list()
        assert_matches_type(CollectionListResponse, collection, path=["response"])

    @parametrize
    def test_raw_response_list(self, client: AlbertAPI) -> None:
        response = client.collections.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = response.parse()
        assert_matches_type(CollectionListResponse, collection, path=["response"])

    @parametrize
    def test_streaming_response_list(self, client: AlbertAPI) -> None:
        with client.collections.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = response.parse()
            assert_matches_type(CollectionListResponse, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    def test_method_delete(self, client: AlbertAPI) -> None:
        collection = client.collections.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    def test_raw_response_delete(self, client: AlbertAPI) -> None:
        response = client.collections.with_raw_response.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = response.parse()
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    def test_streaming_response_delete(self, client: AlbertAPI) -> None:
        with client.collections.with_streaming_response.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = response.parse()
            assert_matches_type(object, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    def test_path_params_delete(self, client: AlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            client.collections.with_raw_response.delete(
                "",
            )


class TestAsyncCollections:
    parametrize = pytest.mark.parametrize("async_client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    async def test_method_create(self, async_client: AsyncAlbertAPI) -> None:
        collection = await async_client.collections.create(
            model="model",
            name="x",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncAlbertAPI) -> None:
        collection = await async_client.collections.create(
            model="model",
            name="x",
            type="public",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    async def test_raw_response_create(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.collections.with_raw_response.create(
            model="model",
            name="x",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = await response.parse()
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.collections.with_streaming_response.create(
            model="model",
            name="x",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = await response.parse()
            assert_matches_type(object, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    async def test_method_list(self, async_client: AsyncAlbertAPI) -> None:
        collection = await async_client.collections.list()
        assert_matches_type(CollectionListResponse, collection, path=["response"])

    @parametrize
    async def test_raw_response_list(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.collections.with_raw_response.list()

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = await response.parse()
        assert_matches_type(CollectionListResponse, collection, path=["response"])

    @parametrize
    async def test_streaming_response_list(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.collections.with_streaming_response.list() as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = await response.parse()
            assert_matches_type(CollectionListResponse, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    async def test_method_delete(self, async_client: AsyncAlbertAPI) -> None:
        collection = await async_client.collections.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    async def test_raw_response_delete(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.collections.with_raw_response.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        collection = await response.parse()
        assert_matches_type(object, collection, path=["response"])

    @parametrize
    async def test_streaming_response_delete(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.collections.with_streaming_response.delete(
            "182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            collection = await response.parse()
            assert_matches_type(object, collection, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    async def test_path_params_delete(self, async_client: AsyncAlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            await async_client.collections.with_raw_response.delete(
                "",
            )
