# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import ParseBetaParseResponse

# pyright: reportDeprecated=false

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestParseBeta:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_parse(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            parse_beta = client.parse_beta.parse(
                file=b"raw file contents",
            )

        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_parse_with_all_params(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            parse_beta = client.parse_beta.parse(
                file=b"raw file contents",
                force_ocr=True,
                page_range="page_range",
            )

        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_parse(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = client.parse_beta.with_raw_response.parse(
                file=b"raw file contents",
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        parse_beta = response.parse()
        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_parse(self, client: Opengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            with client.parse_beta.with_streaming_response.parse(
                file=b"raw file contents",
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                parse_beta = response.parse()
                assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncParseBeta:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_parse(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            parse_beta = await async_client.parse_beta.parse(
                file=b"raw file contents",
            )

        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_parse_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            parse_beta = await async_client.parse_beta.parse(
                file=b"raw file contents",
                force_ocr=True,
                page_range="page_range",
            )

        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_parse(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            response = await async_client.parse_beta.with_raw_response.parse(
                file=b"raw file contents",
            )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        parse_beta = await response.parse()
        assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_parse(self, async_client: AsyncOpengatellm) -> None:
        with pytest.warns(DeprecationWarning):
            async with async_client.parse_beta.with_streaming_response.parse(
                file=b"raw file contents",
            ) as response:
                assert not response.is_closed
                assert response.http_request.headers.get("X-Stainless-Lang") == "python"

                parse_beta = await response.parse()
                assert_matches_type(ParseBetaParseResponse, parse_beta, path=["response"])

        assert cast(Any, response.is_closed) is True
