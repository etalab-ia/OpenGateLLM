from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.domain.model.errors import UnsupportedEndpointError
from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model._modelhttpclient import ModelHttpClient
from api.infrastructure.http.model.exchanges import FormattedModelRequest, FormattedModelResponse, ModelHttpExchange, OriginalModelResponse
from api.schemas.usage import Usage
from api.tests.unit.infrastructure.http.model.factories import ModelHttpExchangeFactory, OriginalModelRequestFactory, UserModelRequestFactory


@pytest.fixture
def model_http_client() -> ModelHttpClient:
    return ModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        metrics_logger=Mock(),
        request_manager=Mock(),
    )


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


def test_build_request_exchange_should_format_request(model_http_client, mocker):
    user_request = UserModelRequestFactory(audio_transcriptions=True)
    method, url = HTTPMethod.POST, "https://test.com/v1/audio/transcriptions"
    mocker.patch.object(type(model_http_client.ENDPOINT_TABLE), "get_method_and_url", return_value=(method, url))
    formatted_request = FormattedModelRequest(method=method, url=url, body={}, form={}, files={})
    adapter = model_http_client._adapters[user_request.endpoint]
    mocked_format = mocker.patch.object(adapter, "format_request", return_value=formatted_request)

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


def test_complete_response_exchange_should_format_original_response_without_usage_computer(model_http_client, mocker):
    original_request = OriginalModelRequestFactory(audio_transcriptions=True)
    original_response = OriginalModelResponse(data={"text": "audio"}, latency=10)
    formatted_response = FormattedModelResponse(data=None)
    exchange = ModelHttpExchangeFactory(original_request=original_request)
    adapter = model_http_client._adapters[original_request.endpoint]
    mocked_format_response = mocker.patch.object(adapter, "format_response", return_value=formatted_response)
    mocked_get_usage = mocker.patch.object(model_http_client.request_manager, "get_usage", return_value=Usage(completion_tokens=10))
    mocked_get_request_id = mocker.patch.object(model_http_client.request_manager, "get_request_id", return_value="request-id")

    result = model_http_client.complete_response_exchange(
        exchange=exchange,
        response_data={"text": "audio"},
        latency=10,
    )

    mocked_get_request_id.assert_called_once()
    mocked_get_usage.assert_called_once()
    model_http_client.request_manager.set_usage.assert_not_called()
    mocked_format_response.assert_called_once_with(exchange=exchange, request_id="request-id", usage=Usage(completion_tokens=10))
    assert result == ModelHttpExchange(original_request=original_request, original_response=original_response, formatted_response=formatted_response)


def test_complete_response_exchange_should_format_original_response_with_usage_computer(model_http_client, mocker):
    model_http_client.usage_computer = Mock()
    original_request = OriginalModelRequestFactory(audio_transcriptions=True)
    original_response = OriginalModelResponse(data={"text": "audio"}, latency=10)
    formatted_response = FormattedModelResponse(data=None)
    exchange = ModelHttpExchangeFactory(original_request=original_request)
    adapter = model_http_client._adapters[original_request.endpoint]
    mocked_format_response = mocker.patch.object(adapter, "format_response", return_value=formatted_response)
    mocked_get_usage = mocker.patch.object(model_http_client.request_manager, "get_usage", return_value=Usage(completion_tokens=10))
    mocked_compute_usage = mocker.patch.object(model_http_client.usage_computer, "compute", return_value=Usage(completion_tokens=100))
    mocked_get_request_id = mocker.patch.object(model_http_client.request_manager, "get_request_id", return_value="request-id")

    result = model_http_client.complete_response_exchange(
        exchange=exchange,
        response_data={"text": "audio"},
        latency=10,
    )

    mocked_get_request_id.assert_called_once()
    mocked_get_usage.assert_called_once()
    mocked_compute_usage.assert_called_once()
    model_http_client.request_manager.set_usage.assert_called_once_with(Usage(completion_tokens=100))

    mocked_format_response.assert_called_once_with(exchange=exchange, request_id="request-id", usage=Usage(completion_tokens=100))
    assert result == ModelHttpExchange(original_request=original_request, original_response=original_response, formatted_response=formatted_response)


def test_get_request_id_should_return_original_response_id_when_present(model_http_client):
    model_http_client.request_manager.get_request_id.return_value = "context-id"
    exchange = ModelHttpExchangeFactory(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {"id": "response-id"}})

    result = model_http_client._get_request_id(exchange=exchange)
    assert result == "response-id"


def test_get_request_id_should_generate_id_when_request_manager_id_is_none(model_http_client, monkeypatch):
    model_http_client.request_manager.get_request_id.return_value = None
    exchange = ModelHttpExchangeFactory(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {}})
    monkeypatch.setattr("api.infrastructure.http.model._modelhttpclient.uuid4", lambda: "12345678-1234-5678-1234-567812345678")

    result = model_http_client._get_request_id(exchange=exchange)
    assert result == "request-12345678123456781234567812345678"


def test_get_request_id_should_return_request_manager_id_when_available(model_http_client):
    model_http_client.request_manager.get_request_id.return_value = "context-id"
    exchange = ModelHttpExchangeFactory(original_request=OriginalModelRequestFactory(models=True), original_response={"data": {}})

    result = model_http_client._get_request_id(exchange=exchange)
    assert result == "context-id"
