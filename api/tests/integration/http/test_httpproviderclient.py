import base64
from urllib.parse import urljoin

import httpx
import pytest
import respx

from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderOriginalResponse, ProviderType
from api.infrastructure.http import HttpProviderClient
from api.tests.integration.factories.mistral import MistralMetricsResponseFactory
from api.tests.integration.factories.vllm import VllmEmbeddingsResponseFactory, VllmMetricsResponseFactory, VllmModelsResponseFactory
from api.tests.unit.infrastructure.factories import ProviderFormattedRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
DEFAULT_MODEL_ID = "test/my-model"


def provider_factory():
    return ProviderFactory(
        type=ProviderType.VLLM,
        url=DEFAULT_PROVIDER_URL,
        key="test-key",
        timeout=1,
        model_name=DEFAULT_MODEL_ID,
    )


@pytest.mark.asyncio(loop_scope="session")
class TestHttpProviderClient:
    @respx.mock
    async def test_forward_request_models(self):
        provider = provider_factory()
        formatted_request = ProviderFormattedRequestFactory(vllm_models=True, base_url=provider.url)

        body = VllmModelsResponseFactory(model_id=DEFAULT_MODEL_ID)
        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmModelsResponseFactory._status_code,
                json=body,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert isinstance(result, ProviderOriginalResponse)
        assert result.data == body
        assert result.text is None
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") == "Bearer test-key"

    @respx.mock
    async def test_forward_request_embeddings(self):
        provider = ProviderFactory(
            type=ProviderType.VLLM,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
        )
        formatted_request = ProviderFormattedRequestFactory(vllm_embeddings=True, base_url=provider.url)

        body = VllmEmbeddingsResponseFactory(model_id=DEFAULT_MODEL_ID, dimensions=8)
        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/embeddings")
        route = respx.post(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmEmbeddingsResponseFactory._status_code,
                json=body,
                headers={"Content-Type": "application/json"},
            )
        )

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert isinstance(result, ProviderOriginalResponse)
        assert result.data == body
        assert result.text is None
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") is None

    @respx.mock
    async def test_forward_request_metrics_text_response(self):
        provider = provider_factory()
        formatted_request = ProviderFormattedRequestFactory(vllm_metrics=True, base_url=provider.url)

        body = VllmMetricsResponseFactory(model_name=DEFAULT_MODEL_ID, running=2.0, waiting=1.0)
        url = urljoin(DEFAULT_PROVIDER_URL, "/metrics")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=VllmMetricsResponseFactory._status_code,
                text=body["text"],
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert isinstance(result, ProviderOriginalResponse)
        assert result.data is None
        assert result.text == body["text"]
        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") == "Bearer test-key"

    @respx.mock
    async def test_forward_request_uses_basic_auth_when_formatted_request_has_auth(self):
        provider = ProviderFactory(
            type=ProviderType.MISTRAL,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
        )
        formatted_request = ProviderFormattedRequestFactory(mistral_metrics=True, base_url=provider.url)

        body = MistralMetricsResponseFactory(model_name=DEFAULT_MODEL_ID)
        url = urljoin(DEFAULT_PROVIDER_URL, "/metrics")
        route = respx.get(url=url).mock(
            return_value=httpx.Response(
                status_code=MistralMetricsResponseFactory._status_code,
                text=body["text"],
                headers={"Content-Type": "text/plain"},
            )
        )

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert isinstance(result, ProviderOriginalResponse)
        assert result.text == body["text"]
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
    async def test_forward_request_returns_too_busy_error_when_provider_request_fails(self, exception, expected_detail):
        provider = provider_factory()
        formatted_request = ProviderFormattedRequestFactory(vllm_models=True, base_url=provider.url)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(side_effect=exception)

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert result == TooBusyModelError(status_code=500, detail=expected_detail)
        assert route.called is True

    @respx.mock
    async def test_forward_request_returns_unknown_error_when_provider_request_raises_unexpected_exception(self):
        provider = provider_factory()
        formatted_request = ProviderFormattedRequestFactory(vllm_models=True, base_url=provider.url)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(side_effect=ValueError("invalid provider response"))

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

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
    async def test_forward_request_returns_status_code_error_when_provider_returns_error_response(self, response, expected_detail):
        provider = provider_factory()
        formatted_request = ProviderFormattedRequestFactory(vllm_models=True, base_url=provider.url)

        url = urljoin(DEFAULT_PROVIDER_URL, "/v1/models")
        route = respx.get(url=url).mock(return_value=response)

        result = await HttpProviderClient().forward_request(provider=provider, formatted_request=formatted_request)

        assert result == StatusCodeModelError(status_code=response.status_code, detail=expected_detail)
        assert route.called is True
