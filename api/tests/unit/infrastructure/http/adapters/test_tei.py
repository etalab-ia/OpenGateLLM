from http import HTTPMethod
from unittest.mock import Mock, patch

import pytest

from api.domain.embeddings.entities import CreateEmbeddingsBody, Embeddings
from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
    ResponseMetrics,
)
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.infrastructure.http.adapters.tei import (
    TeiAudioTranscriptionAdapter,
    TeiChatCompletionAdapter,
    TeiEmbeddingsAdapter,
    TeiModelsAdapter,
    TeiOcrAdapter,
    TeiRerankAdapter,
)
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory, TeiModelsResponseFactory, TeiRerankResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def tei_provider():
    return ProviderFactory(type=ProviderType.TEI, url="https://tei.test", model_name="test/tei-model")


@pytest.fixture
def tei_audio_transcription_adapter(tei_provider) -> TeiAudioTranscriptionAdapter:
    return TeiAudioTranscriptionAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


@pytest.fixture
def tei_chat_completion_adapter(tei_provider) -> TeiChatCompletionAdapter:
    return TeiChatCompletionAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


@pytest.fixture
def tei_embeddings_adapter(tei_provider) -> TeiEmbeddingsAdapter:
    adapter = TeiEmbeddingsAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)
    adapter.model_tokenizer.encode = Mock(return_value=[100, 200])
    adapter.model_environmental_impacts_computer.compute = Mock(return_value=EnvironmentalImpacts(kgCO2eq=1, kWh=2))

    return adapter


@pytest.fixture
def tei_models_adapter(tei_provider) -> TeiModelsAdapter:
    return TeiModelsAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


@pytest.fixture
def tei_ocr_adapter(tei_provider) -> TeiOcrAdapter:
    return TeiOcrAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


@pytest.fixture
def tei_rerank_adapter(tei_provider) -> TeiRerankAdapter:
    return TeiRerankAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


class TestTeiAudioTranscriptionAdapter:
    def test_should_have_no_target_endpoint_route(self, tei_audio_transcription_adapter: TeiAudioTranscriptionAdapter):
        # Assert
        assert tei_audio_transcription_adapter.TARGET_ENDPOINT_ROUTE is None


class TestTeiChatCompletionAdapter:
    def test_should_have_no_target_endpoint_route(self, tei_chat_completion_adapter: TeiChatCompletionAdapter):
        # Assert
        assert tei_chat_completion_adapter.TARGET_ENDPOINT_ROUTE is None


class TestTeiEmbeddingsAdapter:
    def test_should_have_embeddings_target_endpoint_route(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Assert
        assert tei_embeddings_adapter.TARGET_ENDPOINT_ROUTE == "/v1/embeddings"

    @pytest.mark.parametrize(
        "input",
        ["Hello, this is a test.", ["Hello, this is a test.", "This is another test."], [1, 2, 3, 4, 5], [[1, 2, 3], [4, 5, 6]]],
    )
    def test_compute_prompt_tokens_with_string_input(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(embeddings=True)
        original_request.body.input = "Hello, this is a test."
        tei_embeddings_adapter.model_tokenizer = Mock()
        tei_embeddings_adapter.model_tokenizer.encode = Mock(return_value=[100, 200])

        # Act
        result = tei_embeddings_adapter.compute_prompt_tokens(original_request)

        # Assert
        tei_embeddings_adapter.model_tokenizer.encode.assert_called_with("Hello, this is a test.")
        assert result == 2

    def test_compute_prompt_tokens_with_list_of_strings_input(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):  # Arrange
        original_request = ProviderOriginalRequestFactory(embeddings=True)
        original_request.body.input = ["Hello, this is a test.", "This is another test."]
        tei_embeddings_adapter.model_tokenizer = Mock()
        tei_embeddings_adapter.model_tokenizer.encode = Mock(return_value=[100, 200])

        # Act
        result = tei_embeddings_adapter.compute_prompt_tokens(original_request)

        # Assert
        tei_embeddings_adapter.model_tokenizer.encode.assert_called_with("Hello, this is a test. This is another test.")
        assert result == 2

    def test_compute_prompt_tokens_with_list_of_integers_input(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(embeddings=True)
        original_request.body.input = [1, 2, 3, 4, 5]
        tei_embeddings_adapter.model_tokenizer = Mock()
        tei_embeddings_adapter.model_tokenizer.encode = Mock(return_value=[100, 200])

        # Act
        result = tei_embeddings_adapter.compute_prompt_tokens(original_request)

        # Assert
        tei_embeddings_adapter.model_tokenizer.encode.assert_called_with("1 2 3 4 5")
        assert result == 2

    def test_compute_prompt_tokens_with_list_of_lists_of_integers_input(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(embeddings=True)
        original_request.body.input = [[1, 2, 3], [4, 5, 6]]
        tei_embeddings_adapter.model_tokenizer = Mock()
        tei_embeddings_adapter.model_tokenizer.encode = Mock(return_value=[100, 200])

        # Act
        result = tei_embeddings_adapter.compute_prompt_tokens(original_request)

        # Assert
        tei_embeddings_adapter.model_tokenizer.encode.assert_called_with("1 2 3 4 5 6")
        assert result == 2

    def test_should_format_embeddings_request_preserve_body(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(
            endpoint=EndpointRoute.EMBEDDINGS,
            body=CreateEmbeddingsBody(input="Hello, this is a test.", model="test-model", dimensions=1536, encoding_format="float"),
        )

        # Act
        result = tei_embeddings_adapter.format_request(original_request)

        # Assert
        assert result == ProviderFormattedRequest(
            method=HTTPMethod.POST,
            url="https://tei.test/v1/embeddings",
            body={"model": "test-model", "input": "Hello, this is a test.", "dimensions": 1536, "encoding_format": "float"},
        )

    def test_should_format_embeddings_response_correctly(self, tei_embeddings_adapter: TeiEmbeddingsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(embeddings=True)
        response_data = TeiEmbeddingsResponseFactory(dimensions=3)
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        with patch("api.infrastructure.http.adapters._endpointadapter.uuid4", return_value="123"):
            result = tei_embeddings_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert result == ProviderFormattedResponse(
            data=Embeddings(
                id="request-123",
                model="openweight-embeddings",
                data=[{"embedding": response_data["data"][0]["embedding"], "index": 0, "object": "embedding"}],
                usage=Usage(total_tokens=0),
            ),
            metrics=ResponseMetrics(latency=10),
        )


class TestTeiModelsAdapter:
    def test_should_use_info_target_route(self, tei_models_adapter: TeiModelsAdapter):
        # Assert
        assert tei_models_adapter.TARGET_ENDPOINT_ROUTE == "/info"

    def test_should_format_models_request_with_info_route(self, tei_models_adapter: TeiModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)

        # Act
        result = tei_models_adapter.format_request(original_request)

        # Assert
        assert result == ProviderFormattedRequest(method=HTTPMethod.GET, url="https://tei.test/info")

    def test_should_format_models_response_using_max_input_length(self, tei_models_adapter: TeiModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)
        response_data = TeiModelsResponseFactory(model_id="BAAI/bge-reranker-v2-m3", max_context_length=8192)
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        result = tei_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert result == ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id="BAAI/bge-reranker-v2-m3",
                        created=0,
                        owned_by="tei",
                        max_context_length=8192,
                        type=ModelType.TEXT_GENERATION,
                    )
                ]
            ),
            metrics=ResponseMetrics(latency=10),
        )


@pytest.mark.parametrize(
    "adapter_cls",
    [TeiAudioTranscriptionAdapter, TeiChatCompletionAdapter, TeiOcrAdapter],
)
class TestTeiDisabledAdapters:
    def test_should_have_no_target_endpoint_route(self, tei_provider, adapter_cls):
        # Arrange
        adapter = adapter_cls(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)

        # Assert
        assert adapter.TARGET_ENDPOINT_ROUTE is None


class TestTeiRerankAdapter:
    def test_should_use_rerank_target_route(self, tei_rerank_adapter: TeiRerankAdapter):
        # Assert
        assert tei_rerank_adapter.TARGET_ENDPOINT_ROUTE == "/rerank"

    def test_should_format_rerank_request_with_rerank_route(self, tei_rerank_adapter: TeiRerankAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = tei_rerank_adapter.format_request(original_request)

        # Assert
        assert result.method == HTTPMethod.POST
        assert result.url == "https://tei.test/rerank"
        assert result.body["query"] == original_request.body.query
        assert result.body["texts"] == original_request.body.documents
        assert result.body["raw_scores"] is False
        assert result.body["return_text"] is False
        assert result.body["truncate"] is False
        assert result.body["truncation_direction"] == "right"

    def test_should_format_rerank_response_sorted_by_score_and_limited_to_top_n(self, tei_rerank_adapter: TeiRerankAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)
        response_data = TeiRerankResponseFactory(
            data=[
                {"index": 0, "score": 0.72},
                {"index": 2, "score": 0.95},
                {"index": 1, "score": 0.50},
            ]
        )
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        with patch("api.infrastructure.http.adapters.tei.uuid4", return_value="123"):
            result = tei_rerank_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert result.data.id == "request-123"
        assert result.data.usage.total_tokens == 0
        assert result.metrics == ResponseMetrics(latency=10)
