from contextvars import ContextVar
from http import HTTPMethod

import pytest

from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
    ResponseMetrics,
)
from api.domain.rerank.entities import Rerank, RerankResult
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http.adapters.tei import (
    TeiAudioTranscriptionAdapter,
    TeiChatCompletionAdapter,
    TeiModelsAdapter,
    TeiOcrAdapter,
    TeiRerankAdapter,
)
from api.tests.integration.factories.tei import TeiModelsResponseFactory, TeiRerankResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def tei_provider():
    return ProviderFactory(type=ProviderType.TEI, url="https://tei.test", model_name="test/tei-model")


@pytest.fixture
def request_context() -> ContextVar[RequestContext]:
    context = ContextVar("request_context")
    context.set(RequestContext())
    return context


@pytest.fixture
def tei_models_adapter(tei_provider) -> TeiModelsAdapter:
    return TeiModelsAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


@pytest.fixture
def tei_rerank_adapter(tei_provider) -> TeiRerankAdapter:
    return TeiRerankAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=tei_provider)


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

    def test_should_format_models_response_using_max_input_length(
        self, tei_models_adapter: TeiModelsAdapter, request_context: ContextVar[RequestContext]
    ):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)
        response_data = TeiModelsResponseFactory(model_id="BAAI/bge-reranker-v2-m3", max_context_length=8192)
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        result = tei_models_adapter.format_response(
            original_response=original_response,
            original_request=original_request,
            request_context=request_context,
        )

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

    def test_should_format_rerank_response_sorted_by_score_and_limited_to_top_n(
        self, tei_rerank_adapter: TeiRerankAdapter, request_context: ContextVar[RequestContext]
    ):
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
        result = tei_rerank_adapter.format_response(
            original_response=original_response,
            original_request=original_request,
            request_context=request_context,
        )

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.data == Rerank(
            id=request_context.get().id,
            model=original_request.body.model,
            results=[
                RerankResult(index=2, relevance_score=0.95),
                RerankResult(index=0, relevance_score=0.72),
            ],
        )
        assert result.data.usage.total_tokens == 0
        assert result.metrics == ResponseMetrics(latency=10)
