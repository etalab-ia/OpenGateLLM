from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.infrastructure.http.model.adapters import AudioTranscriptionAdapter, ChatCompletionAdapter, EmbeddingsAdapter, OcrAdapter
from api.infrastructure.http.model.tei import TeiModelHttpClient
from api.infrastructure.http.model.tei.adapters import TeiModelsAdapter, TeiRerankAdapter
from api.utils.variables import EndpointRoute


@pytest.fixture
def tei_model_http_client() -> TeiModelHttpClient:
    return TeiModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        metrics_logger=Mock(),
        request_manager=Mock(),
    )


class TestTeiModelHttpClient:
    def test_endpoint_table_should_disable_audio_transcriptions(self, tei_model_http_client: TeiModelHttpClient):
        # Arrange
        mocked_url = tei_model_http_client.url

        # Act
        method, url = tei_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mocked_url, endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS)

        # Assert
        assert (method, url) == (None, None)

    def test_endpoint_table_should_disable_chat_completions(self, tei_model_http_client: TeiModelHttpClient):
        # Arrange
        mocked_url = tei_model_http_client.url

        # Act
        method, url = tei_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mocked_url, endpoint=EndpointRoute.CHAT_COMPLETIONS)

        # Assert
        assert (method, url) == (None, None)

    def test_endpoint_table_should_disable_ocr(self, tei_model_http_client: TeiModelHttpClient):
        # Arrange
        mocked_url = tei_model_http_client.url

        # Act
        method, url = tei_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mocked_url, endpoint=EndpointRoute.OCR)

        # Assert
        assert (method, url) == (None, None)

    def test_endpoint_table_should_override_models_endpoint(self, tei_model_http_client: TeiModelHttpClient):
        # Arrange
        mocked_url = tei_model_http_client.url

        # Act
        method, url = tei_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mocked_url, endpoint=EndpointRoute.MODELS)

        # Assert
        assert (method, url) == (HTTPMethod.GET, "https://test.com/info")

    def test_endpoint_table_should_override_rerank_endpoint(self, tei_model_http_client: TeiModelHttpClient):
        # Arrange
        mocked_url = tei_model_http_client.url

        # Act
        method, url = tei_model_http_client.ENDPOINT_TABLE.get_method_and_url(base_url=mocked_url, endpoint=EndpointRoute.RERANK)

        # Assert
        assert (method, url) == (HTTPMethod.POST, "https://test.com/rerank")

    def test_build_adapters_should_register_tei_specific_adapters(self, tei_model_http_client: TeiModelHttpClient):
        # Act
        adapters = tei_model_http_client._adapters

        # Assert
        assert isinstance(adapters[EndpointRoute.MODELS], TeiModelsAdapter)
        assert isinstance(adapters[EndpointRoute.RERANK], TeiRerankAdapter)

        assert isinstance(adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS], AudioTranscriptionAdapter)
        assert isinstance(adapters[EndpointRoute.CHAT_COMPLETIONS], ChatCompletionAdapter)
        assert isinstance(adapters[EndpointRoute.EMBEDDINGS], EmbeddingsAdapter)
        assert isinstance(adapters[EndpointRoute.OCR], OcrAdapter)
