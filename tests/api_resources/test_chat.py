# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import ChatCreateCompletionResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestChat:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create_completion(self, client: Opengatellm) -> None:
        chat = client.chat.create_completion(
            messages=[{}],
            model="model",
        )
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_create_completion_with_all_params(self, client: Opengatellm) -> None:
        chat = client.chat.create_completion(
            messages=[{}],
            model="model",
            frequency_penalty=0,
            logit_bias={"foo": 0},
            logprobs=True,
            max_completion_tokens=0,
            max_tokens=0,
            n=0,
            parallel_tool_calls=True,
            presence_penalty=0,
            response_format={},
            search=True,
            search_args={
                "collections": [0],
                "k": 1,
                "limit": 1,
                "method": "hybrid",
                "offset": 0,
                "rff_k": 0,
                "score_threshold": 0,
                "template": "template",
            },
            seed=0,
            stop="string",
            stream=True,
            stream_options={},
            temperature=0,
            tool_choice={},
            tools=[{}],
            top_logprobs=0,
            top_p=0,
            user="user",
        )
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_create_completion(self, client: Opengatellm) -> None:
        response = client.chat.with_raw_response.create_completion(
            messages=[{}],
            model="model",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chat = response.parse()
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_create_completion(self, client: Opengatellm) -> None:
        with client.chat.with_streaming_response.create_completion(
            messages=[{}],
            model="model",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            chat = response.parse()
            assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncChat:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create_completion(self, async_client: AsyncOpengatellm) -> None:
        chat = await async_client.chat.create_completion(
            messages=[{}],
            model="model",
        )
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_create_completion_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        chat = await async_client.chat.create_completion(
            messages=[{}],
            model="model",
            frequency_penalty=0,
            logit_bias={"foo": 0},
            logprobs=True,
            max_completion_tokens=0,
            max_tokens=0,
            n=0,
            parallel_tool_calls=True,
            presence_penalty=0,
            response_format={},
            search=True,
            search_args={
                "collections": [0],
                "k": 1,
                "limit": 1,
                "method": "hybrid",
                "offset": 0,
                "rff_k": 0,
                "score_threshold": 0,
                "template": "template",
            },
            seed=0,
            stop="string",
            stream=True,
            stream_options={},
            temperature=0,
            tool_choice={},
            tools=[{}],
            top_logprobs=0,
            top_p=0,
            user="user",
        )
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_create_completion(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.chat.with_raw_response.create_completion(
            messages=[{}],
            model="model",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        chat = await response.parse()
        assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_create_completion(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.chat.with_streaming_response.create_completion(
            messages=[{}],
            model="model",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            chat = await response.parse()
            assert_matches_type(ChatCreateCompletionResponse, chat, path=["response"])

        assert cast(Any, response.is_closed) is True
