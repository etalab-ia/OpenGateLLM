# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, cast

import pytest

from opengatellm import Opengatellm, AsyncOpengatellm
from tests.utils import assert_matches_type
from opengatellm.types import AudioTranscribeResponse

base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:4010")


class TestAudio:
    parametrize = pytest.mark.parametrize("client", [False, True], indirect=True, ids=["loose", "strict"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_transcribe(self, client: Opengatellm) -> None:
        audio = client.audio.transcribe(
            file=b"raw file contents",
            model="model",
        )
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_method_transcribe_with_all_params(self, client: Opengatellm) -> None:
        audio = client.audio.transcribe(
            file=b"raw file contents",
            model="model",
            language="af",
            prompt="prompt",
            response_format="json",
            temperature=0,
        )
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_raw_response_transcribe(self, client: Opengatellm) -> None:
        response = client.audio.with_raw_response.transcribe(
            file=b"raw file contents",
            model="model",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        audio = response.parse()
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    def test_streaming_response_transcribe(self, client: Opengatellm) -> None:
        with client.audio.with_streaming_response.transcribe(
            file=b"raw file contents",
            model="model",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            audio = response.parse()
            assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

        assert cast(Any, response.is_closed) is True


class TestAsyncAudio:
    parametrize = pytest.mark.parametrize(
        "async_client", [False, True, {"http_client": "aiohttp"}], indirect=True, ids=["loose", "strict", "aiohttp"]
    )

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_transcribe(self, async_client: AsyncOpengatellm) -> None:
        audio = await async_client.audio.transcribe(
            file=b"raw file contents",
            model="model",
        )
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_method_transcribe_with_all_params(self, async_client: AsyncOpengatellm) -> None:
        audio = await async_client.audio.transcribe(
            file=b"raw file contents",
            model="model",
            language="af",
            prompt="prompt",
            response_format="json",
            temperature=0,
        )
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_raw_response_transcribe(self, async_client: AsyncOpengatellm) -> None:
        response = await async_client.audio.with_raw_response.transcribe(
            file=b"raw file contents",
            model="model",
        )

        assert response.is_closed is True
        assert response.http_request.headers.get("X-Stainless-Lang") == "python"
        audio = await response.parse()
        assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

    @pytest.mark.skip(reason="Mock server tests are disabled")
    @parametrize
    async def test_streaming_response_transcribe(self, async_client: AsyncOpengatellm) -> None:
        async with async_client.audio.with_streaming_response.transcribe(
            file=b"raw file contents",
            model="model",
        ) as response:
            assert not response.is_closed
            assert response.http_request.headers.get("X-Stainless-Lang") == "python"

            audio = await response.parse()
            assert_matches_type(AudioTranscribeResponse, audio, path=["response"])

        assert cast(Any, response.is_closed) is True
