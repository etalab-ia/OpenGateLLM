# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type
from albert_api.types import Documents

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestDocuments:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_list(self, client: AlbertAPI) -> None:
        document = client.documents.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    def test_method_list_with_all_params(self, client: AlbertAPI) -> None:
        document = client.documents.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            limit=1,
            offset="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    def test_raw_response_list(self, client: AlbertAPI) -> None:
        response = client.documents.with_raw_response.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        document = response.parse()
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    def test_streaming_response_list(self, client: AlbertAPI) -> None:
        with client.documents.with_streaming_response.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            document = response.parse()
            assert_matches_type(Documents, document, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    def test_path_params_list(self, client: AlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            client.documents.with_raw_response.list(
                collection="",
            )

    @parametrize
    def test_method_delete(self, client: AlbertAPI) -> None:
        document = client.documents.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(object, document, path=["response"])

    @parametrize
    def test_raw_response_delete(self, client: AlbertAPI) -> None:
        response = client.documents.with_raw_response.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        document = response.parse()
        assert_matches_type(object, document, path=["response"])

    @parametrize
    def test_streaming_response_delete(self, client: AlbertAPI) -> None:
        with client.documents.with_streaming_response.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            document = response.parse()
            assert_matches_type(object, document, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    def test_path_params_delete(self, client: AlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            client.documents.with_raw_response.delete(
                document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
                collection="",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `document` but received ''"):
            client.documents.with_raw_response.delete(
                document="",
                collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            )


class TestAsyncDocuments:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @parametrize
    async def test_method_list(self, async_client: AsyncAlbertAPI) -> None:
        document = await async_client.documents.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    async def test_method_list_with_all_params(self, async_client: AsyncAlbertAPI) -> None:
        document = await async_client.documents.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            limit=1,
            offset="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    async def test_raw_response_list(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.documents.with_raw_response.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        document = await response.parse()
        assert_matches_type(Documents, document, path=["response"])

    @parametrize
    async def test_streaming_response_list(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.documents.with_streaming_response.list(
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            document = await response.parse()
            assert_matches_type(Documents, document, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    async def test_path_params_list(self, async_client: AsyncAlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            await async_client.documents.with_raw_response.list(
                collection="",
            )

    @parametrize
    async def test_method_delete(self, async_client: AsyncAlbertAPI) -> None:
        document = await async_client.documents.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )
        assert_matches_type(object, document, path=["response"])

    @parametrize
    async def test_raw_response_delete(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.documents.with_raw_response.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        document = await response.parse()
        assert_matches_type(object, document, path=["response"])

    @parametrize
    async def test_streaming_response_delete(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.documents.with_streaming_response.delete(
            document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            document = await response.parse()
            assert_matches_type(object, document, path=["response"])

        assert cast(Any, response.is_closed) is True

    @parametrize
    async def test_path_params_delete(self, async_client: AsyncAlbertAPI) -> None:
        with pytest.raises(ValueError, match=r"Expected a non-empty value for `collection` but received ''"):
            await async_client.documents.with_raw_response.delete(
                document="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
                collection="",
            )

        with pytest.raises(ValueError, match=r"Expected a non-empty value for `document` but received ''"):
            await async_client.documents.with_raw_response.delete(
                document="",
                collection="182bd5e5-6e1a-4fe4-a799-aa6d9a6ab26e",
            )
