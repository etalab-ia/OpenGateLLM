from http import HTTPMethod

from api.infrastructure.http.model import ModelHttpClientEndpoints
from api.utils.variables import EndpointRoute


class TestModelHttpClientEndpoints:
    def test_get_method_and_url_should_return_audio_transcriptions_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.AUDIO_TRANSCRIPTIONS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"
        # Act

        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.POST, "https://test.com/v1/audio/transcriptions")

    def test_get_method_and_url_should_return_chat_completions_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.CHAT_COMPLETIONS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.POST, "https://test.com/v1/chat/completions")

    def test_get_method_and_url_should_return_embeddings_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.EMBEDDINGS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.POST, "https://test.com/v1/embeddings")

    def test_get_method_and_url_should_return_models_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.MODELS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.GET, "https://test.com/v1/models")

    def test_get_method_and_url_should_return_ocr_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.OCR
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.POST, "https://test.com/v1/ocr")

    def test_get_method_and_url_should_return_rerank_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.RERANK
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.POST, "https://test.com/v1/rerank")

    def test_get_method_and_url_should_conserves_subdomain_with_trailing_slash(self):
        # Arrange
        endpoint = EndpointRoute.MODELS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/provider/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.GET, "https://test.com/provider/v1/models")

    def test_get_method_and_url_should_conserves_subdomain_without_trailing_slash(self):
        # Arrange
        endpoint = EndpointRoute.MODELS
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/provider"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (HTTPMethod.GET, "https://test.com/provider/v1/models")

    def test_get_method_and_url_should_return_none_for_unsupported_endpoint(self):
        # Arrange
        endpoint = EndpointRoute.SEARCH
        table = ModelHttpClientEndpoints()
        mocked_url = "https://test.com/"

        # Act
        result = table.get_method_and_url(base_url=mocked_url, endpoint=endpoint)

        # Assert
        assert result == (None, None)
