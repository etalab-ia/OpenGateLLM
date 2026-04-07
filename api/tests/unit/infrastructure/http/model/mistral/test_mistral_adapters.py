import base64
from http import HTTPMethod

from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model.exchanges import FormattedModelRequest, FormattedModelResponse, OriginalModelResponse
from api.infrastructure.http.model.mistral.adapters import MistralAudioTranscriptionAdapter, MistralChatCompletionAdapter, MistralModelsAdapter
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat
from api.schemas.usage import Usage
from api.tests.integration.factories.mistral import (
    MistralAudioTranscriptionResponseFactory,
    MistralModelResponseFactory,
    MistralModelsResponseFactory,
)
from api.tests.unit.infrastructure.http.model.factories import ModelHttpExchangeFactory, OriginalModelRequestFactory


class TestMistralAudioTranscriptionAdapter:
    def test_should_format_valid_original_request(self, mocker):
        # Arrange
        original_request = OriginalModelRequestFactory(audio_transcriptions=True)
        mocker.patch.object(base64, "b64encode", return_value=b"mock-base64-encoded-audio")
        method, url = HTTPMethod.POST, "https://test.com/v1/chat/completions"
        adapter = MistralAudioTranscriptionAdapter()
        mock_model_name = "test-model"

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=mock_model_name)

        # Assert
        assert result == FormattedModelRequest(
            method=method,
            url=url,
            body={
                "model": mock_model_name,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_audio", "input_audio": "mock-base64-encoded-audio"},
                            {"type": "text", "text": original_request.form["prompt"]},
                        ],
                    },
                ],
                "stream": False,
            },
        )

    def test_should_format_valid_original_response_with_json_response_format(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=OriginalModelResponse(data=MistralAudioTranscriptionResponseFactory(), latency=10),
        )
        adapter = MistralAudioTranscriptionAdapter()
        mock_usage = Usage()
        mock_request_id = "request-1234567890"

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == FormattedModelResponse(
            data=AudioTranscription(
                id=mock_request_id,
                model=exchange.original_request.form["model"],
                text=exchange.original_response.data["choices"][0]["message"]["content"],
                usage=mock_usage.model_dump(),
            ),
        )

    def test_should_format_valid_original_response_with_text_response_format(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(audio_transcriptions=True),
            original_response=OriginalModelResponse(data=MistralAudioTranscriptionResponseFactory(), latency=10),
        )
        exchange.original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = MistralAudioTranscriptionAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == FormattedModelResponse(text=exchange.original_response.data["choices"][0]["message"]["content"], data=None)


class TestMistralChatCompletionAdapter:
    def test_should_format_valid_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(chat_completions=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/chat/completions", "test-model"

        # Act
        adapter = MistralChatCompletionAdapter()
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == FormattedModelRequest(
            method=method,
            url=url,
            body={
                "frequency_penalty": 0.0,
                "max_tokens": None,
                "messages": original_request.body.get("messages"),
                "model": "test-model",
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


class TestMistralModelsAdapter:
    def test_should_format_valid_original_response(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            original_response=OriginalModelResponse(
                data=MistralModelsResponseFactory(
                    data=[
                        MistralModelResponseFactory(
                            model_id="mistral-medium-2508",
                            created=1773667856,
                            owned_by="mistralai",
                            max_context_length=131072,
                            aliases=["mistral-medium-latest"],
                        ),
                        MistralModelResponseFactory(
                            model_id="mistral-ocr-2512",
                            created=1773667856,
                            owned_by="mistralai",
                            max_context_length=16384,
                            aliases=["mistral-ocr-latest"],
                        ),
                    ]
                )
            ),
        )
        adapter = MistralModelsAdapter()
        mock_request_id = "request-1234567890"
        mock_usage = Usage()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == FormattedModelResponse(
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
                        id="mistral-ocr-2512",
                        aliases=["mistral-ocr-latest"],
                        created=1773667856,
                        owned_by="mistralai",
                        max_context_length=16384,
                    ),
                ]
            )
        )
