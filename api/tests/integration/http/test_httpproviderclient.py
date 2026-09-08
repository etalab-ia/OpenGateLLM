import base64
from unittest.mock import patch
from urllib.parse import urljoin

import httpx
import pytest
import respx

from api.domain.embeddings.entities import CreateEmbeddingsBody
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderRequest, ProviderResponse, ProviderType
from api.domain.provider.errors import (
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)
from api.infrastructure.http import HttpProviderAdapterBuilder, HttpProviderClient
from api.infrastructure.http.adapters.models.vllm import VllmModelsAdapter
from api.tests.integration.factories.mistral import MistralMetricsResponseFactory
from api.tests.integration.factories.vllm import VllmEmbeddingsResponseFactory, VllmMetricsResponseFactory, VllmModelsResponseFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
DEFAULT_MODEL_ID = "test/my-model"


def provider_factory(**overrides):
    values = dict(
        type=ProviderType.VLLM,
        url=DEFAULT_PROVIDER_URL,
        key="test-key",
        timeout=1,
        model_name=DEFAULT_MODEL_ID,
    )
    values.update(overrides)
    return ProviderFactory(**values)


def http_provider_client() -> HttpProviderClient:
    return HttpProviderClient(adapter_builder=HttpProviderAdapterBuilder())


@pytest.mark.asyncio(loop_scope="session")
class TestHttpProviderClient:
    @respx.mock
    async def test_forward_models(self):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)

        body = VllmModelsResponseFactory(model_id=DEFAULT_MODEL_ID)
        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmModelsResponseFactory._status_code,
                json=body,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await http_provider_client().forward(provider=provider, request=request)

        assert isinstance(result, ProviderResponse)
        assert [model.id for model in result.data.data] == [DEFAULT_MODEL_ID]
        assert result.text is None
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") == "Bearer test-key"

    @respx.mock
    async def test_forward_embeddings(self):
        provider = provider_factory(key=None)
        request = ProviderRequest(
            endpoint=EndpointRoute.EMBEDDINGS,
            payload=CreateEmbeddingsBody(model="openweight-embeddings", input=["hello world"]),
        )

        body = VllmEmbeddingsResponseFactory(model_id=DEFAULT_MODEL_ID, dimensions=8)
        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/embeddings")
        route = respx.post(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmEmbeddingsResponseFactory._status_code,
                json=body,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await http_provider_client().forward(provider=provider, request=request)

        assert isinstance(result, ProviderResponse)
        assert len(result.data.data[0].embedding) == 8
        assert result.text is None
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") is None

    @respx.mock
    async def test_forward_metrics_text_response(self):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.METRICS)

        body = VllmMetricsResponseFactory(model_name=DEFAULT_MODEL_ID, running=2.0, waiting=1.0)
        url = urljoin(DEFAULT_PROVIDER_URL, "/metrics")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmMetricsResponseFactory._status_code,
                text=body["text"],
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await http_provider_client().forward(provider=provider, request=request)

        assert isinstance(result, ProviderResponse)
        assert result.data.running_requests == 2.0
        assert result.data.waiting_requests == 1.0
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") == "Bearer test-key"

    @respx.mock
    async def test_forward_uses_basic_auth_when_provider_has_basic_auth(self):
        provider = ProviderFactory(
            type=ProviderType.MISTRAL,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
            basic_auth={"username": "metrics", "password": "secret"},
        )
        request = ProviderRequest(endpoint=EndpointRoute.METRICS)

        body = MistralMetricsResponseFactory(model_name=DEFAULT_MODEL_ID)
        url = urljoin(DEFAULT_PROVIDER_URL, "/metrics")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=MistralMetricsResponseFactory._status_code,
                text=body["text"],
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await http_provider_client().forward(provider=provider, request=request)

        assert isinstance(result, ProviderResponse)
        assert result.data is not None
        assert route.called is True
        expected_auth = "Basic " + base64.b64encode(b"metrics:secret").decode()
        assert route.calls[0].request.headers.get("Authorization") == expected_auth

    @pytest.mark.parametrize(
        ("exception", "expected_detail"),
        [
            (httpx.TimeoutException("timeout"), "TimeoutException"),
            (httpx.ReadTimeout("read timeout"), "ReadTimeout"),
            (httpx.ConnectTimeout("connect timeout"), "ConnectTimeout"),
            (httpx.WriteTimeout("write timeout"), "WriteTimeout"),
            (httpx.PoolTimeout("pool timeout"), "PoolTimeout"),
            (httpx.RemoteProtocolError("remote protocol error"), "RemoteProtocolError"),
            (httpx.ConnectError("connect error"), "ConnectError"),
        ],
    )
    @respx.mock
    async def test_forward_returns_too_busy_error_when_provider_request_fails(self, exception, expected_detail):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(side_effect=exception)

        result = await http_provider_client().forward(provider=provider, request=request)

        assert result == TooBusyModelError(status_code=500, detail=expected_detail)
        assert route.called is True

    @respx.mock
    async def test_forward_returns_unknown_error_when_provider_request_raises_unexpected_exception(self):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(side_effect=ValueError("invalid provider response"))

        result = await http_provider_client().forward(provider=provider, request=request)

        assert result == UnknownModelError(status_code=500, detail="invalid provider response")
        assert route.called is True

    @pytest.mark.parametrize(
        ("response", "expected_detail"),
        [
            (
                httpx.Response(
                    status_code=400,
                    json={"message": "{'error': 'bad request'}"},
                    headers={"Content-Type": "application/json"},
                ),
                {"error": "bad request"},
            ),
            (
                httpx.Response(
                    status_code=401,
                    json={"message": "unauthorized"},
                    headers={"Content-Type": "application/json"},
                ),
                "unauthorized",
            ),
            (
                httpx.Response(
                    status_code=503,
                    text="service unavailable",
                    headers={"Content-Type": "text/plain"},
                ),
                "service unavailable",
            ),
        ],
    )
    @respx.mock
    async def test_forward_returns_status_code_error_when_provider_returns_error_response(self, response, expected_detail):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(return_value=response)

        result = await http_provider_client().forward(provider=provider, request=request)

        assert result == StatusCodeModelError(status_code=response.status_code, detail=expected_detail)
        assert route.called is True

    async def test_forward_returns_unsupported_provider_endpoint_error_when_adapter_is_missing(self):
        provider = provider_factory(type=ProviderType.ALBERT)
        request = ProviderRequest(endpoint=EndpointRoute.METRICS)

        result = await http_provider_client().forward(provider=provider, request=request)

        assert result == UnsupportedProviderEndpointError(endpoint=EndpointRoute.METRICS, provider_type=ProviderType.ALBERT)

    async def test_forward_returns_request_validation_error_when_adapter_rejects_request(self):
        provider = provider_factory()
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)
        validation_error = ProviderAdapterValidationRequestError(provider_type=provider.type, errors=[{"msg": "invalid"}])

        with patch.object(VllmModelsAdapter, "to_http_request", return_value=validation_error):
            result = await http_provider_client().forward(provider=provider, request=request)

        assert result is validation_error

    @respx.mock
    async def test_forward_returns_response_validation_error_when_the_provider_payload_does_not_parse(self):
        provider = provider_factory()
        request = ProviderRequest(
            endpoint=EndpointRoute.EMBEDDINGS,
            payload=CreateEmbeddingsBody(model="openweight-embeddings", input=["hello world"]),
        )

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/embeddings")
        route = respx.post(url=url).mock(
            return_value=httpx.Response(
                status_code=200,
                json={"data": [{"embedding": "not-a-vector", "index": 0, "object": "embedding"}], "object": "list"},
                headers={"Content-Type": "application/json"},
            )
        )

        result = await http_provider_client().forward(provider=provider, request=request)

        assert isinstance(result, ProviderAdapterValidationResponseError)
        assert result.provider_type == ProviderType.VLLM
        assert route.called is True
