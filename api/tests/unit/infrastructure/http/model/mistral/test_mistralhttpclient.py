from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.infrastructure.http.model.adapters import EmbeddingsAdapter, OcrAdapter, RerankAdapter
from api.infrastructure.http.model.mistral import MistralModelHttpClient
from api.infrastructure.http.model.mistral.adapters import MistralAudioTranscriptionAdapter, MistralChatCompletionAdapter, MistralModelsAdapter
from api.utils.variables import EndpointRoute


@pytest.fixture
def mistral_model_http_client() -> MistralModelHttpClient:
    return MistralModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="mistral-test-model",
        metrics_logger=Mock(),
        request_manager=Mock(),
    )


class TestMistralModelHttpClient:
    def test_endpoint_table_should_override_audio_transcriptions_endpoint(self, mistral_model_http_client: MistralModelHttpClient):
        # Arrange
        endpoint = EndpointRoute.AUDIO_TRANSCRIPTIONS
        # Act
        method, url = mistral_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mistral_model_http_client.url, endpoint=endpoint)

        # Assert
        assert method == HTTPMethod.POST
        assert url == "https://test.com/v1/chat/completions"

    def test_endpoint_table_should_return_none_for_rerank_endpoint(self, mistral_model_http_client: MistralModelHttpClient):
        # Arrange
        endpoint = EndpointRoute.RERANK

        # Act
        method, url = mistral_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mistral_model_http_client.url, endpoint=endpoint)

        # Assert
        assert (method, url) == (None, None)

    def test_endpoint_table_should_keep_default_endpoints_for_unchanged_endpoints(self, mistral_model_http_client: MistralModelHttpClient):
        # Arrange
        endpoint = EndpointRoute.OCR

        # Act
        method, url = mistral_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mistral_model_http_client.url, endpoint=endpoint)

        # Assert
        assert (method, url) == (HTTPMethod.POST, "https://test.com/v1/ocr")

    def test_build_adapters_should_register_mistral_specific_adapters(self, mistral_model_http_client: MistralModelHttpClient):
        # Act
        adapters = mistral_model_http_client._adapters

        # Assert
        assert isinstance(adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS], MistralAudioTranscriptionAdapter)
        assert isinstance(adapters[EndpointRoute.CHAT_COMPLETIONS], MistralChatCompletionAdapter)
        assert isinstance(adapters[EndpointRoute.MODELS], MistralModelsAdapter)

        assert isinstance(adapters[EndpointRoute.EMBEDDINGS], EmbeddingsAdapter)
        assert isinstance(adapters[EndpointRoute.OCR], OcrAdapter)
        assert isinstance(adapters[EndpointRoute.RERANK], RerankAdapter)
