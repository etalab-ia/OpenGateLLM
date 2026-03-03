import base64
from copy import deepcopy

import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import MistralModelHttpClient
from api.schemas.audio import AudioTranscription
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.tests.unit.infrastructure.http.factories import (
    FormattedRequestContentFactory,
    MistralAudioTranscriptionResponseFactory,
    MistralModelsResponseFactory,
)
from api.utils.variables import EndpointRoute


@pytest.fixture
def mistral_model_http_client():
    return MistralModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="mistral-test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


@pytest.fixture
def chat_completion_request_content(mistral_model_http_client):
    return FormattedRequestContentFactory(chat_completions=True, model=mistral_model_http_client.model_name)


@pytest.fixture
def audio_transcription_request_content(mistral_model_http_client):
    return FormattedRequestContentFactory(audio_transcriptions=True, model=mistral_model_http_client.model_name)


@pytest.fixture
def mistral_models_request_content(mistral_model_http_client):
    return FormattedRequestContentFactory(models=True, model=mistral_model_http_client.model_name)


@pytest.fixture
def mistral_models_response_data():
    return MistralModelsResponseFactory()


@pytest.fixture
def audio_transcription_response_request_content(mistral_model_http_client):
    return RequestContent(
        method="POST",
        model=mistral_model_http_client.model_name,
        endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
        additional_data={
            "id": "request-1234567890",
            "model": mistral_model_http_client.model_name,
            "usage": Usage(prompt_tokens=10, completion_tokens=10, total_tokens=20).model_dump(),
        },
    )


@pytest.fixture
def mistral_audio_transcription_response_data():
    return MistralAudioTranscriptionResponseFactory()


class TestMistralModelHttpClient:
    def test_should_format_valid_chat_completion_request(self, mistral_model_http_client, chat_completion_request_content):
        request_content = chat_completion_request_content.model_copy(deep=True)

        result = mistral_model_http_client.format_chat_completion_request(request_content)

        assert result.body == {
            "frequency_penalty": 0.0,
            "max_tokens": None,
            "messages": chat_completion_request_content.body.get("messages"),
            "model": chat_completion_request_content.body.get("model"),
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
            "tools": None,
            "top_p": 1.0,
        }

    def test_should_format_audio_transcription_request(self, mistral_model_http_client, audio_transcription_request_content):
        request_content = audio_transcription_request_content.model_copy(deep=True)

        result = mistral_model_http_client.format_audio_transcription_request(request_content)

        expected_audio = base64.b64encode(audio_transcription_request_content.files["file"][1]).decode("utf-8")

        assert result.form == {}
        assert result.files == {}
        assert result.additional_data == {}
        assert result.body == {
            "model": audio_transcription_request_content.form.get("model"),
            "temperature": audio_transcription_request_content.form["temperature"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "input_audio": expected_audio},
                        {"type": "text", "text": audio_transcription_request_content.form["prompt"]},
                    ],
                },
            ],
            "stream": False,
        }

    def test_should_format_response_to_models_format(
        self,
        mistral_model_http_client,
        mistral_models_request_content,
        mistral_models_response_data,
    ):
        request_content = mistral_models_request_content.model_copy(deep=True)
        response_data = deepcopy(mistral_models_response_data)

        result = mistral_model_http_client.format_response_to_models_response(request_content=request_content, response_data=response_data)

        assert result == ModelsResponse(
            data=[
                ModelResponse(
                    id="mistral-medium-2508",
                    type=None,
                    aliases=["mistral-medium-latest"],
                    created=1773667856,
                    owned_by="mistralai",
                    max_context_length=131072,
                ),
                ModelResponse(
                    id="mistral-embed-2312",
                    type=None,
                    aliases=["mistral-embed-2312", "mistral-embed-latest"],
                    created=1773667856,
                    owned_by="mistralai",
                    max_context_length=8192,
                ),
                ModelResponse(
                    id="mistral-ocr-2512",
                    type=None,
                    aliases=["mistral-ocr-latest"],
                    created=1773667856,
                    owned_by="mistralai",
                    max_context_length=16384,
                ),
            ]
        )

    def test_should_format_response_to_audio_transcription_format(
        self,
        mistral_model_http_client,
        audio_transcription_response_request_content,
        mistral_audio_transcription_response_data,
    ):
        request_content = audio_transcription_response_request_content.model_copy(deep=True)
        response_data = mistral_audio_transcription_response_data

        result = mistral_model_http_client.format_response_to_audio_transcription_response(
            request_content=request_content,
            response_data=response_data,
        )

        assert result == AudioTranscription(
            id=response_data["id"],
            model=response_data["model"],
            text=response_data["choices"][0]["message"]["content"],
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        )
