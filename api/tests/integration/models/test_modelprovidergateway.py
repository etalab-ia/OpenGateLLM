import pytest
import respx

from api.domain.model.entities import ModelType as RouterType
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.context import RequestContextManager
from api.infrastructure.http.model import ModelMetricsLogger
from api.infrastructure.model import ModelProviderGateway
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_embeddings_responses, mock_models_responses
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory, TeiModelsResponseFactory
from api.tests.integration.factories.vllm import VllmModelsResponseFactory, VllmNotFoundResponseFactory

DEFAULT_MODEL_ID = "test/my-model"
DEFAULT_MAX_CONTEXT_LENGTH = 4096
DEFAULT_VECTOR_SIZE = 768


@pytest.fixture
def metrics_logger(redis_client) -> ModelMetricsLogger:
    return ModelMetricsLogger(redis_client=redis_client)


@pytest.fixture
def request_manager() -> RequestContextManager:
    return RequestContextManager()


@pytest.fixture
def gateway(metrics_logger: ModelMetricsLogger, request_manager: RequestContextManager) -> ModelProviderGateway:
    return ModelProviderGateway(metrics_logger=metrics_logger, request_manager=request_manager)


@pytest.mark.asyncio(loop_scope="session")
class TestModelProviderGateway:
    @respx.mock
    async def test_get_capabilities_of_non_embeddings_providers(self, gateway: ModelProviderGateway):
        mock_models_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmModelsResponseFactory(model_id=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH),
            status_code=VllmModelsResponseFactory._status_code,
        )
        mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmNotFoundResponseFactory(),
            status_code=VllmNotFoundResponseFactory._status_code,
        )

        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.VLLM,
            url=DEFAULT_PROVIDER_URL,
            key="test-key",
            timeout=1,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=DEFAULT_MAX_CONTEXT_LENGTH, vector_size=None)

    @respx.mock
    async def test_get_capabilities_of_embeddings_providers(self, gateway: ModelProviderGateway):
        mock_models_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiModelsResponseFactory(model_id=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH),
            status_code=TeiModelsResponseFactory._status_code,
        )
        mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
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
        )

        assert result == ProviderCapabilities(max_context_length=DEFAULT_MAX_CONTEXT_LENGTH, vector_size=DEFAULT_VECTOR_SIZE)
