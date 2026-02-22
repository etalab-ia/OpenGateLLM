# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import OcrExtractTextResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestOcr:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_extract_text(self, client: Opengatellm) -> None:
        ocr = client.ocr.extract_text(
            document={"document_url": "document_url"},
        )
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_extract_text_with_all_params(self, client: Opengatellm) -> None:
        ocr = client.ocr.extract_text(
            document={
                "document_url": "document_url",
                "document_name": "document_name",
                "type": "document_url",
            },
            bbox_annotation_format={
                "json_schema": {
                    "name": "name",
                    "schema_definition": {"foo": "bar"},
                    "description": "description",
                    "strict": True,
                },
                "type": "text",
            },
            document_annotation_format={
                "json_schema": {
                    "name": "name",
                    "schema_definition": {"foo": "bar"},
                    "description": "description",
                    "strict": True,
                },
                "type": "text",
            },
            image_limit=0,
            image_min_size=0,
            include_image_base64=True,
            model="model",
            pages=[0],
        )
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_extract_text(self, client: Opengatellm) -> None:
        response = client.ocr.with_raw_response.extract_text(
            document={"document_url": "document_url"},
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        ocr = response.parse()
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_extract_text(self, client: Opengatellm) -> None:
        with client.ocr.with_streaming_response.extract_text(
            document={"document_url": "document_url"},
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            ocr = response.parse()
            assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncOcr:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_extract_text(self, async_client: AsyncOpengatellm) -> None:
        ocr = await async_client.ocr.extract_text(
            document={"document_url": "document_url"},
        )
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_extract_text_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        ocr = await async_client.ocr.extract_text(
            document={
                "document_url": "document_url",
                "document_name": "document_name",
                "type": "document_url",
            },
            bbox_annotation_format={
                "json_schema": {
                    "name": "name",
                    "schema_definition": {"foo": "bar"},
                    "description": "description",
                    "strict": True,
                },
                "type": "text",
            },
            document_annotation_format={
                "json_schema": {
                    "name": "name",
                    "schema_definition": {"foo": "bar"},
                    "description": "description",
                    "strict": True,
                },
                "type": "text",
            },
            image_limit=0,
            image_min_size=0,
            include_image_base64=True,
            model="model",
            pages=[0],
        )
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_extract_text(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.ocr.with_raw_response.extract_text(
            document={"document_url": "document_url"},
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        ocr = await response.parse()
        assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_extract_text(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.ocr.with_streaming_response.extract_text(
            document={"document_url": "document_url"},
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            ocr = await response.parse()
            assert_matches_type(OcrExtractTextResponse, ocr, path=["response"])

        assert cast(Any, response.is_closed) is True
