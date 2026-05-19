from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.infrastructure.http.model.adapters import AudioTranscriptionAdapter, ChatCompletionAdapter, EmbeddingsAdapter, OcrAdapter, RerankAdapter
from api.infrastructure.http.model.vllm import VllmModelHttpClient
from api.infrastructure.http.model.vllm.adapters import VllmModelsAdapter
from api.utils.variables import EndpointRoute


@pytest.fixture
def vllm_model_http_client() -> VllmModelHttpClient:
    return VllmModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="vllm-test-model",
        provider_metrics_logger=Mock(),
        request_manager=Mock(),
    )


class TestVllmModelHttpClient:
    def test_endpoint_table_should_override_rerank_endpoint(self, vllm_model_http_client: VllmModelHttpClient):
        # Arrange
        endpoint = EndpointRoute.RERANK

        # Act
        method, url = vllm_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=vllm_model_http_client.url, endpoint=endpoint)

        # Assert
        assert (method, url) == (HTTPMethod.POST, "https://test.com/v2/rerank")

    def test_endpoint_table_should_keep_default_endpoints_for_unchanged_endpoints(self, vllm_model_http_client: VllmModelHttpClient):
        # Arrange
        endpoint = EndpointRoute.CHAT_COMPLETIONS

        # Act
        method, url = vllm_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=vllm_model_http_client.url, endpoint=endpoint)

        # Assert
        assert (method, url) == (HTTPMethod.POST, "https://test.com/v1/chat/completions")

    def test_build_adapters_should_register_vllm_specific_models_adapter(self, vllm_model_http_client: VllmModelHttpClient):
        # Act
        adapters = vllm_model_http_client._adapters

        # Assert
        assert isinstance(adapters[EndpointRoute.MODELS], VllmModelsAdapter)

        assert isinstance(adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS], AudioTranscriptionAdapter)
        assert isinstance(adapters[EndpointRoute.CHAT_COMPLETIONS], ChatCompletionAdapter)
        assert isinstance(adapters[EndpointRoute.EMBEDDINGS], EmbeddingsAdapter)
        assert isinstance(adapters[EndpointRoute.OCR], OcrAdapter)
        assert isinstance(adapters[EndpointRoute.RERANK], RerankAdapter)
