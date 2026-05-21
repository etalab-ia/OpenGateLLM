from contextvars import ContextVar
from urllib.parse import urljoin

import httpx
import pytest
import respx

from api.domain.model.entities import ModelType as RouterType
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http import HttpProviderClient
from api.infrastructure.model import ModelProviderGateway
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory, TeiModelsResponseFactory
from api.tests.integration.factories.vllm import VllmModelsResponseFactory

DEFAULT_PROVIDER_URL = "http://my-test-provider/"
DEFAULT_MODEL_ID = "test/my-model"
DEFAULT_MAX_CONTEXT_LENGTH = 4096
DEFAULT_VECTOR_SIZE = 768

MODELS_ENDPOINT_BY_PROVIDER = {ProviderType.VLLM: "/v1/models", ProviderType.TEI: "/info"}
EMBEDDINGS_ENDPOINT = "/v1/embeddings"


def _mock_models_response(respx_mock, provider_type: ProviderType, body: dict, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, MODELS_ENDPOINT_BY_PROVIDER[provider_type])
    respx_mock.get(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


def _mock_embeddings_response(respx_mock, body: dict, status_code: int) -> None:
    url = urljoin(DEFAULT_PROVIDER_URL, EMBEDDINGS_ENDPOINT)
    respx_mock.post(url=url).mock(return_value=httpx.Response(status_code=status_code, json=body))


@pytest.fixture
def request_context() -> ContextVar[RequestContext]:
    context = ContextVar("request_context")
    context.set(RequestContext())
    return context


@pytest.fixture
def gateway() -> ModelProviderGateway:
    return ModelProviderGateway(provider_client=HttpProviderClient())


@pytest.mark.asyncio(loop_scope="session")
class TestModelProviderGateway:
    @respx.mock
    async def test_get_capabilities_of_non_embeddings_providers(
        self,
        gateway: ModelProviderGateway,
        request_context: ContextVar[RequestContext],
    ):
        _mock_models_response(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmModelsResponseFactory(model_id=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH),
            status_code=VllmModelsResponseFactory._status_code,
        )

        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.VLLM,
            url=DEFAULT_PROVIDER_URL,
            key="test-key",
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
            request_context=request_context,
        )

        assert result == ProviderCapabilities(max_context_length=DEFAULT_MAX_CONTEXT_LENGTH, vector_size=None)

    @respx.mock
    async def test_get_capabilities_of_embeddings_providers(
        self,
        gateway: ModelProviderGateway,
        request_context: ContextVar[RequestContext],
    ):
        _mock_models_response(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiModelsResponseFactory(model_id=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH),
            status_code=TeiModelsResponseFactory._status_code,
        )
        _mock_embeddings_response(
            respx_mock=respx,
            body=TeiEmbeddingsResponseFactory(model_id=DEFAULT_MODEL_ID, dimensions=DEFAULT_VECTOR_SIZE),
            status_code=TeiEmbeddingsResponseFactory._status_code,
        )

        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key="test-key",
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
            request_context=request_context,
        )

        assert result == ProviderCapabilities(max_context_length=DEFAULT_MAX_CONTEXT_LENGTH, vector_size=DEFAULT_VECTOR_SIZE)
