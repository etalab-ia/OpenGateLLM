from http import HTTPMethod

import pytest

from api.domain.model.errors import UnsupportedEndpointError
from api.domain.provider.entities import ProviderCarbonFootprintZone, ProviderType
from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.infrastructure.http.model import (
    FormattedModelRequest,
    FormattedModelResponse,
    ModelHttpClient,
    ModelHttpExchange,
    OriginalModelResponse,
)
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat
from api.schemas.chat import ChatCompletion
from api.schemas.core.context import RequestContext
from api.schemas.embeddings import Embeddings
from api.schemas.ocr import OCR
from api.schemas.rerank import RerankResult, Reranks
from api.schemas.usage import Usage
from api.tests.unit.infrastructure.http.factories.common import OriginalModelRequestFactory, UserModelRequestFactory
from api.tests.unit.infrastructure.http.factories.mistral import MistralOriginalResponseFactory
from api.tests.unit.infrastructure.http.factories.openai import OpenaiOriginalResponseFactory
from api.tests.unit.infrastructure.http.factories.vllm import VllmOriginalResponseFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def model_http_client() -> ModelHttpClient:
    return ModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


def test_get_method_and_url_should_return_audio_transcriptions_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS)

    assert result == (HTTPMethod.POST, "https://test.com/v1/audio/transcriptions")


def test_get_method_and_url_should_return_chat_completions_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.CHAT_COMPLETIONS)

    assert result == (HTTPMethod.POST, "https://test.com/v1/chat/completions")


def test_get_method_and_url_should_return_embeddings_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.EMBEDDINGS)

    assert result == (HTTPMethod.POST, "https://test.com/v1/embeddings")


def test_get_method_and_url_should_return_models_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.MODELS)

    assert result == (HTTPMethod.GET, "https://test.com/v1/models")


def test_get_method_and_url_should_return_ocr_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.OCR)

    assert result == (HTTPMethod.POST, "https://test.com/v1/ocr")


def test_get_method_and_url_should_return_rerank_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.RERANK)

    assert result == (HTTPMethod.POST, "https://test.com/v1/rerank")


def test_get_method_and_url_should_lstrip_leading_slash_before_urljoin(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url="https://test.com/provider/", endpoint=EndpointRoute.MODELS)

    assert result == (HTTPMethod.GET, "https://test.com/provider/v1/models")


def test_get_method_and_url_should_return_none_for_unsupported_endpoint(model_http_client):
    result = model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=model_http_client.url, endpoint=EndpointRoute.SEARCH)

    assert result == (None, None)


def test_build_request_exchange_should_return_unsupported_endpoint_error_when_method_is_none(model_http_client, mocker):
    user_request = OriginalModelRequestFactory(models=True)
    model_http_client.TYPE = ProviderType.OPENAI
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(None, "https://test.com/v1/chat/completions"))

    result = model_http_client.build_request_exchange(user_request=user_request)

    assert result == UnsupportedEndpointError(endpoint=user_request.endpoint, provider_type=model_http_client.TYPE)


def test_build_request_exchange_should_return_unsupported_endpoint_error_when_url_is_none(model_http_client, mocker):
    user_request = OriginalModelRequestFactory(models=True)
    model_http_client.TYPE = ProviderType.OPENAI
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(HTTPMethod.GET, None))

    result = model_http_client.build_request_exchange(user_request=user_request)

    assert result == UnsupportedEndpointError(endpoint=user_request.endpoint, provider_type=model_http_client.TYPE)


# Test request formatting methods
def test_build_request_exchange_should_format_audio_transcription_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(audio_transcriptions=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/audio/transcriptions"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_audio_transcription_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_build_request_exchange_should_format_chat_completion_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(chat_completions=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/chat/completions"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_chat_completion_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_build_request_exchange_should_format_models_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(models=True)
    method, url = HTTPMethod.GET, "https://test.com/v1/models"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_models_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_build_request_exchange_should_format_embeddings_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(embeddings=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/embeddings"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_embeddings_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_build_request_exchange_should_format_ocr_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(ocr=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/ocr"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_ocr_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_build_request_exchange_should_format_rerank_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(rerank=True)
    method, url = HTTPMethod.POST, "/v1/rerank"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    mocked_format = mocker.patch.object(model_http_client, "get_formatted_rerank_request", return_value=formatted_request)

    result = model_http_client.build_request_exchange(user_request=user_request)

    mocked_format.assert_called_once()
    assert isinstance(result, ModelHttpExchange)
    assert result.original_request == OriginalModelRequestFactory(
        endpoint=user_request.endpoint,
        body=user_request.body,
        form=user_request.form,
        files=user_request.files,
    )
    assert result.formatted_request == formatted_request


def test_should_format_valid_audio_transcription_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(audio_transcriptions=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/audio/transcription"

    # Act
    result = model_http_client.get_formatted_audio_transcription_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        form={
            "model": "test-model",
            "language": "fr",
            "prompt": original_request.form["prompt"],
            "temperature": 0.3,
            "response_format": "json",
        },
        files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
    )


def test_should_format_audio_transcription_request_with_text_response_format_to_json_response_format(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(audio_transcriptions=True)
    original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT.value
    method, url = HTTPMethod.POST, "https://test.com/v1/audio/transcription"

    # Act
    result = model_http_client.get_formatted_audio_transcription_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        form={
            "model": "test-model",
            "language": "fr",
            "prompt": original_request.form["prompt"],
            "temperature": 0.3,
            "response_format": "json",
        },
        files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
    )


def test_should_format_valid_chat_completion_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(chat_completions=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/chat/completions"

    # Act
    result = model_http_client.get_formatted_chat_completion_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        body={
            "model": "test-model",
            "messages": original_request.body["messages"],
            "frequency_penalty": None,
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
            "seed": 10,
            "stop": None,
            "stream": False,
            "logit_bias": None,
            "logprobs": False,
            "top_logprobs": None,
            "presence_penalty": 0.0,
            "max_completion_tokens": None,
            "n": 1,
            "stream_options": None,
            "temperature": None,
            "top_p": None,
            "parallel_tool_calls": False,
            "user": None,
            "search": False,
            "search_args": None,
        },
    )


def test_should_format_valid_embeddings_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(embeddings=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/embeddings"

    # Act
    result = model_http_client.get_formatted_embeddings_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        body={"model": "test-model", "input": original_request.body["input"], "dimensions": 1536, "encoding_format": "float"},
    )


def test_should_format_valid_models_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(models=True)
    method, url = HTTPMethod.GET, "https://test.com/v1/models"

    # Act
    result = model_http_client.get_formatted_models_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(method=method, url=url)


def test_should_format_valid_ocr_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(ocr=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/ocr"

    # Act
    result = model_http_client.get_formatted_ocr_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        body={
            "model": "test-model",
            "bbox_annotation_format": None,
            "document": original_request.body["document"],
            "document_annotation_format": None,
            "image_limit": 10,
            "image_min_size": None,
            "include_image_base64": True,
            "pages": [1, 2, 3],
        },
    )


def test_should_format_valid_rerank_request(model_http_client):
    # Arrange
    original_request = OriginalModelRequestFactory(rerank=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/rerank"

    # Act
    result = model_http_client.get_formatted_rerank_request(original_request=original_request, method=method, url=url)

    # Assert
    assert result == FormattedModelRequest(
        method=method,
        url=url,
        body={
            "model": "test-model",
            "query": original_request.body["query"],
            "documents": original_request.body["documents"],
            "top_n": 2,
        },
    )


# Test response formatting methods
def test_complete_response_exchange_should_format_audio_transcription_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(audio_transcriptions=True))
    mocked_format = mocker.patch.object(model_http_client, "format_audio_transcription_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"text": "audio"}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"text": "audio"}, latency=10)
    assert result == exchange


def test_complete_response_exchange_should_format_chat_completion_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(chat_completions=True))
    mocked_format = mocker.patch.object(model_http_client, "format_chat_completion_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"id": "chat-id"}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"id": "chat-id"}, latency=10)
    assert result == exchange


def test_complete_response_exchange_should_format_embeddings_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(embeddings=True))
    mocked_format = mocker.patch.object(model_http_client, "format_embeddings_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"data": []}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"data": []}, latency=10)
    assert result == exchange


def test_complete_response_exchange_should_format_models_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(models=True))
    mocked_format = mocker.patch.object(model_http_client, "format_models_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"data": []}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"data": []}, latency=10)
    assert result == exchange


def test_complete_response_exchange_should_format_ocr_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(ocr=True))
    mocked_format = mocker.patch.object(model_http_client, "format_ocr_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"pages": []}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"pages": []}, latency=10)
    assert result == exchange


def test_complete_response_exchange_should_format_rerank_original_response(model_http_client, mocker):
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(rerank=True))
    mocked_format = mocker.patch.object(model_http_client, "format_rerank_original_response", return_value=exchange)

    result = model_http_client.complete_response_exchange(exchange=exchange, response_data={"results": []}, latency=10)

    mocked_format.assert_called_once()
    assert mocked_format.call_args.kwargs["exchange"].original_response == OriginalModelResponse(data={"results": []}, latency=10)
    assert result == exchange


def test_should_format_valid_audio_transcription_original_response(model_http_client, mocker):
    """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(audio_transcriptions=True),
        original_response=VllmOriginalResponseFactory(audio_transcriptions=True),
    )
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_audio_transcription_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=AudioTranscription(
            id=mock_request_id,
            model="openweight-audio",
            text=exchange.original_response.data["text"],
            usage=mock_usage.model_dump(),
        ),
    )


def test_should_format_audio_transcription_original_response_with_text_response_format(model_http_client, mocker):
    """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(audio_transcriptions=True),
        original_response=VllmOriginalResponseFactory(audio_transcriptions=True),
    )
    exchange.original_request.form["response_format"] = AudioTranscriptionResponseFormat.TEXT.value
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_audio_transcription_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(text=exchange.original_response.data["text"], data=None)


def test_should_format_valid_chat_completion_original_response(model_http_client, mocker):
    """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(chat_completions=True),
        original_response=VllmOriginalResponseFactory(chat_completions=True),
    )
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_chat_completion_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=ChatCompletion(
            id=mock_request_id,
            model="openweight-large",
            choices=[
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "logprobs": None,
                    "message": {
                        "annotations": None,
                        "audio": None,
                        "content": exchange.original_response.data["choices"][0]["message"]["content"],
                        "function_call": None,
                        "reasoning": exchange.original_response.data["choices"][0]["message"]["reasoning"],
                        "refusal": None,
                        "role": "assistant",
                        "tool_calls": [],
                    },
                    "stop_reason": None,
                    "token_ids": None,
                }
            ],
            created=1774879102,
            kv_transfer_params=None,
            object="chat.completion",
            prompt_logprobs=None,
            prompt_token_ids=None,
            service_tier=None,
            system_fingerprint=None,
            usage=mock_usage.model_dump(),
        ),
        text=None,
    )


def test_should_format_valid_embeddings_original_response(model_http_client, mocker):
    """Using the Vllm response factory because the responses are not overriden by VllM child provider class (see VllmModelHttpClient)."""

    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(embeddings=True),
        original_response=VllmOriginalResponseFactory(embeddings=True),
    )
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_embeddings_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=Embeddings(
            id=mock_request_id,
            model="openweight-embeddings",
            data=[{"embedding": [-0.30128387, 0.5073153, -0.807378], "index": 0, "object": "embedding"}],
            usage=mock_usage.model_dump(),
        ),
        text=None,
    )


def test_should_format_valid_models_original_response(model_http_client, mocker):
    """Using the OpenAI response factory because the responses are not overriden by OpenAI child provider class (see OpenaiModelHttpClient)."""

    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(models=True),
        original_response=OpenaiOriginalResponseFactory(models=True),
    )

    # Act
    result = model_http_client.format_models_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=ModelsResponse(
            object="list",
            data=[
                {"created": 1686588896, "type": None, "aliases": [], "id": "gpt-4-0613", "object": "model", "owned_by": "openai"},
                {"created": 1687882411, "type": None, "aliases": [], "id": "gpt-4", "object": "model", "owned_by": "openai"},
                {"created": 1677610602, "type": None, "aliases": [], "id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
                {"created": 1773451123, "type": None, "aliases": [], "id": "gpt-5.4-mini", "object": "model", "owned_by": "system"},
                {"created": 1772691852, "type": None, "aliases": [], "id": "gpt-5.4", "object": "model", "owned_by": "system"},
            ],
        ),
        text=None,
    )


def test_should_format_valid_ocr_original_response(model_http_client, mocker):
    """Using the Mistral response factory because the responses are not overriden by Mistral child provider class (see MistralModelHttpClient)."""
    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(ocr=True),
        original_response=MistralOriginalResponseFactory(ocr=True),
    )
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_ocr_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=OCR(
            document_annotation=None,
            id=mock_request_id,
            model="openweight-ocr",
            pages=[
                {
                    "dimensions": {"dpi": 200, "height": 1969, "width": 1575},
                    "footer": None,
                    "header": None,
                    "hyperlinks": ["http://en.wikibooks.org/", "http://en.wikibooks.org/wiki/Sensory_Systems"],
                    "images": [
                        {
                            "bottom_right_x": 946,
                            "bottom_right_y": 1695,
                            "id": "img-0.jpeg",
                            "image_annotation": None,
                            "image_base64": exchange.original_response.data["pages"][0]["images"][0]["image_base64"],
                            "top_left_x": 151,
                            "top_left_y": 1071,
                        }
                    ],
                    "index": 0,
                    "markdown": exchange.original_response.data["pages"][0]["markdown"],
                    "tables": [],
                },
                {
                    "dimensions": {"dpi": 200, "height": 1969, "width": 1575},
                    "footer": None,
                    "header": None,
                    "hyperlinks": [],
                    "images": [],
                    "index": 1,
                    "markdown": exchange.original_response.data["pages"][1]["markdown"],
                    "tables": [],
                },
            ],
            usage_info={"doc_size_bytes": 135171, "pages_processed": 2},
            usage=mock_usage.model_dump(),
        ),
        text=None,
    )


def test_should_format_valid_rerank_original_response(model_http_client, mocker):
    """Using the Vllm response factory because the responses are not overriden by VLLM child provider class (see VllmModelHttpClient)."""
    # Arrange
    exchange = ModelHttpExchange(
        original_request=OriginalModelRequestFactory(rerank=True),
        original_response=VllmOriginalResponseFactory(rerank=True),
    )
    mock_request_id = "request-1234567890"
    mock_usage = Usage()
    mocker.patch.object(model_http_client, "_get_request_id", return_value=mock_request_id)
    mocker.patch.object(model_http_client, "_get_usage", return_value=mock_usage)

    # Act
    result = model_http_client.format_rerank_original_response(exchange=exchange)

    # Assert
    assert result.formatted_response == FormattedModelResponse(
        data=Reranks(
            id=mock_request_id,
            model="openweight-rerank",
            results=[
                RerankResult(index=3, relevance_score=0.999071),
                RerankResult(index=4, relevance_score=0.7867867),
                RerankResult(index=0, relevance_score=0.32713068),
            ],
            usage=mock_usage.model_dump(),
        )
    )


def test_get_request_id_should_return_original_response_id_when_present(mocker):
    mocked_request_context = RequestContext(id="context-id")
    mocked_request_context_var = mocker.Mock()
    mocked_request_context_var.get.return_value = mocked_request_context
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {"id": "response-id"}})
    mocker.patch("api.infrastructure.http.model._modelhttpclient.request_context", mocked_request_context_var)

    result = ModelHttpClient._get_request_id(exchange=exchange)
    assert mocked_request_context.id == "response-id"
    assert result == "response-id"


def test_get_request_id_should_generate_id_when_context_id_is_none(mocker, monkeypatch):
    mocked_request_context = RequestContext(id=None)
    mocked_request_context_var = mocker.Mock()
    mocked_request_context_var.get.return_value = mocked_request_context
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {}})
    monkeypatch.setattr("api.infrastructure.http.model._modelhttpclient.uuid4", lambda: "12345678-1234-5678-1234-567812345678")
    mocker.patch("api.infrastructure.http.model._modelhttpclient.request_context", mocked_request_context_var)

    result = ModelHttpClient._get_request_id(exchange=exchange)
    assert mocked_request_context.id == "request-12345678123456781234567812345678"
    assert result == "request-12345678123456781234567812345678"


def test_get_request_id_should_return_context_id_when_available(mocker):
    mocked_request_context = RequestContext(id="context-id")
    mocked_request_context_var = mocker.Mock()
    mocked_request_context_var.get.return_value = mocked_request_context
    exchange = ModelHttpExchange(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {}})
    mocker.patch("api.infrastructure.http.model._modelhttpclient.request_context", mocked_request_context_var)

    result = ModelHttpClient._get_request_id(exchange=exchange)
    assert mocked_request_context.id == "context-id"
    assert result == "context-id"
