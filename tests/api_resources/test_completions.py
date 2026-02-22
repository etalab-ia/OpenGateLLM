# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from albert_api import AlbertAPI, AsyncAlbertAPI
from tests.utils import assert_matches_type
from albert_api.types import Completions

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestCompletions:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @parametrize
    def test_method_create(self, client: AlbertAPI) -> None:
        completion = client.completions.create(
            model="model",
            prompt="string",
        )
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    def test_method_create_with_all_params(self, client: AlbertAPI) -> None:
        completion = client.completions.create(
            model="model",
            prompt="string",
            best_of=0,
            echo=True,
            frequency_penalty=0,
            logit_bias={"foo": 0},
            logprobs=0,
            max_tokens=0,
            n=0,
            presence_penalty=0,
            seed=0,
            stop="string",
            stream=True,
            suffix="suffix",
            temperature=0,
            top_p=0,
            user="user",
        )
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    def test_raw_response_create(self, client: AlbertAPI) -> None:
        response = client.completions.with_raw_response.create(
            model="model",
            prompt="string",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        completion = response.parse()
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    def test_streaming_response_create(self, client: AlbertAPI) -> None:
        with client.completions.with_streaming_response.create(
            model="model",
            prompt="string",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            completion = response.parse()
            assert_matches_type(Completions, completion, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncCompletions:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @parametrize
    async def test_method_create(self, async_client: AsyncAlbertAPI) -> None:
        completion = await async_client.completions.create(
            model="model",
            prompt="string",
        )
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    async def test_method_create_with_all_params(self, async_client: AsyncAlbertAPI) -> None:
        completion = await async_client.completions.create(
            model="model",
            prompt="string",
            best_of=0,
            echo=True,
            frequency_penalty=0,
            logit_bias={"foo": 0},
            logprobs=0,
            max_tokens=0,
            n=0,
            presence_penalty=0,
            seed=0,
            stop="string",
            stream=True,
            suffix="suffix",
            temperature=0,
            top_p=0,
            user="user",
        )
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    async def test_raw_response_create(self, async_client: AsyncAlbertAPI) -> None:
        response = await async_client.completions.with_raw_response.create(
            model="model",
            prompt="string",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        completion = await response.parse()
        assert_matches_type(Completions, completion, path=["response"])

    @parametrize
    async def test_streaming_response_create(self, async_client: AsyncAlbertAPI) -> None:
        async with async_client.completions.with_streaming_response.create(
            model="model",
            prompt="string",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            completion = await response.parse()
            assert_matches_type(Completions, completion, path=["response"])

        assert cast(Any, response.is_closed) is True
