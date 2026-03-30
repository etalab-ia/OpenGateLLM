import base64
from http import HTTPMethod

import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import FormattedModelRequest, FormattedModelResponse, MistralModelHttpClient
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat
from api.schemas.usage import Usage
from api.tests.unit.infrastructure.http.factories.common import HttpModelExchangeFactory, OriginalModelRequestFactory
from api.tests.unit.infrastructure.http.factories.mistral import (
    MistralFormattedModelRequestFactory,
    MistralOriginalResponseFactory,
)


@pytest.fixture
def mistral_model_http_client() -> MistralModelHttpClient:
    return MistralModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="mistral-test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


class TestMistralModelHttpClient:
    def test_should_format_valid_audio_transcription_original_request(self, mistral_model_http_client):
        # Arrange
        exchange = HttpModelExchangeFactory(original_request=OriginalModelRequestFactory(audio_transcriptions=True))

        # Act
        result = mistral_model_http_client.format_audio_transcription_request(exchange=exchange)

        # Assert
        expected_audio = base64.b64encode(exchange.original_request.files["file"][1]).decode("utf-8")

        assert result.formatted_request == FormattedModelRequest(
            method=HTTPMethod.POST,
            endpoint="/v1/chat/completions",
            body={
                "model": mistral_model_http_client.model_name,
                "temperature": exchange.original_request.form["temperature"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_audio", "input_audio": expected_audio},
                            {"type": "text", "text": exchange.original_request.form["prompt"]},
                        ],
                    },
                ],
                "stream": False,
            },
        )

    def test_should_format_valid_chat_completion_original_request(self, mistral_model_http_client):
        # Arrange
        exchange = HttpModelExchangeFactory(original_request=OriginalModelRequestFactory(chat_completions=True))

        # Act
        result = mistral_model_http_client.format_chat_completion_request(exchange=exchange)

        # Assert
        assert result.formatted_request == FormattedModelRequest(
            method=HTTPMethod.POST,
            endpoint="/v1/chat/completions",
            body={
                "frequency_penalty": 0.0,
                "max_tokens": None,
                "messages": exchange.original_request.body.get("messages"),
                "model": mistral_model_http_client.model_name,
                "n": 1,
                "parallel_tool_calls": False,
                "prediction": {},
                "presence_penalty": 0.0,
                "prompt_mode": None,
                "random_seed": 10,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "DummyResponseFormat",
                        "schema": {
                            "properties": {
                                "dummy_list": {"items": {"type": "string"}, "title": "Dummy List", "type": "array"},
                                "dummy_str": {"title": "Dummy Str", "type": "string"},
                                "dummy_optional_bool": {"default": False, "title": "Dummy Optional Bool", "type": "boolean"},
                                "dummy_nullable_int": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Dummy Nullable Int"},
                            },
                            "required": ["dummy_list", "dummy_str", "dummy_nullable_int"],
                            "title": "DummyResponseFormat",
                            "type": "object",
                        },
                    },
                },
                "safe_prompt": False,
                "stop": [],
                "stream": False,
                "temperature": None,
                "tool_choice": "required",
                "tools": [
                    {
                        "type": "function",
                        "name": "get_horoscope",
                        "description": "Get today's horoscope for an astrological sign.",
                        "parameters": {
                            "type": "object",
                            "properties": {"sign": {"type": "string", "description": "An astrological sign like Taurus or Aquarius"}},
                            "required": ["sign"],
                        },
                    },
                ],
                "top_p": 1.0,
            },
        )

    def test_should_format_valid_audio_transcription_original_response_with_json_response_format(self, mistral_model_http_client, mocker):
        # Arrange
        exchange = HttpModelExchangeFactory(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=MistralOriginalResponseFactory(audio_transcription=True),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        mocker.patch.object(mistral_model_http_client, "_get_request_id", return_value=mock_request_id)
        mocker.patch.object(mistral_model_http_client, "_get_usage", return_value=mock_usage)

        # Act
        result = mistral_model_http_client.format_response_to_audio_transcription_response(exchange=exchange)

        # Assert
        assert result.formatted_response == FormattedModelResponse(
            data=AudioTranscription(
                id=mock_request_id,
                model=exchange.original_request.form["model"],
                text=exchange.original_response.data["choices"][0]["message"]["content"],
                usage=mock_usage.model_dump(),
            ),
        )

    def test_should_format_valid_audio_transcription_original_response_with_text_response_format(self, mistral_model_http_client, mocker):
        # Arrange
        exchange = HttpModelExchangeFactory(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=MistralOriginalResponseFactory(audio_transcription=True),
        )
        exchange.original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT.value
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        mocker.patch.object(mistral_model_http_client, "_get_request_id", return_value=mock_request_id)
        mocker.patch.object(mistral_model_http_client, "_get_usage", return_value=mock_usage)

        # Act
        result = mistral_model_http_client.format_response_to_audio_transcription_response(exchange=exchange)

        # Assert
        assert result.formatted_response == FormattedModelResponse(
            text=exchange.original_response.data["choices"][0]["message"]["content"],
            data=None,
        )

    def test_should_format_valid_models_original_response(self, mistral_model_http_client):
        # Arrange
        exchange = HttpModelExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            formatted_request=MistralFormattedModelRequestFactory(models=True),
            original_response=MistralOriginalResponseFactory(models=True),
        )

        # Act
        result = mistral_model_http_client.format_response_to_models_response(exchange=exchange)

        # Assert
        assert result.formatted_response == FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id="mistral-medium-2508",
                        aliases=["mistral-medium-latest"],
                        created=1773667856,
                        owned_by="mistralai",
                        max_context_length=131072,
                    ),
                    ModelResponse(
                        id="mistral-embed-2312",
                        aliases=["mistral-embed-2312", "mistral-embed-latest"],
                        created=1773667856,
                        owned_by="mistralai",
                        max_context_length=8192,
                    ),
                    ModelResponse(
                        id="mistral-ocr-2512",
                        aliases=["mistral-ocr-latest"],
                        created=1773667856,
                        owned_by="mistralai",
                        max_context_length=16384,
                    ),
                ]
            )
        )
