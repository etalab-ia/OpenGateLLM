from urllib.parse import urljoin

import httpx
import pytest
import respx

from api.domain.provider.entities import ProviderOriginalResponse, ProviderType
from api.infrastructure.http import HttpProviderClient
from api.tests.integration.factories.vllm import VllmEmbeddingsResponseFactory, VllmModelsResponseFactory
from api.tests.unit.infrastructure.factories import ProviderFormattedRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
DEFAULT_MODEL_ID = "test/my-model"


@pytest.mark.asyncio(loop_scope="session")
class TestHttpProviderClient:
    @respx.mock
    async def test_forward_request_models(self):
        provider = ProviderFactory(
            type=ProviderType.VLLM,
            url=DEFAULT_PROVIDER_URL,
            key="test-key",
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
        )
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
        assert result.metrics.ttft is None
        assert isinstance(result.metrics.latency, int)
        assert result.metrics.latency >= 0

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
        assert result.metrics.ttft is None
        assert isinstance(result.metrics.latency, int)
        assert result.metrics.latency >= 0

        assert route.called is True
        assert route.calls[0].request.headers.get("Authorization") is None
