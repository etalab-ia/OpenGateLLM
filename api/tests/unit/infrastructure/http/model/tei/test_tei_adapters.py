from http import HTTPMethod

from api.schemas.rerank import Reranks

from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalResponse
from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.infrastructure.http.model.tei.adapters import TeiModelsAdapter, TeiRerankAdapter
from api.schemas.usage import Usage
from api.tests.integration.factories.tei import TeiFormattedModelRequestFactory, TeiModelsResponseFactory, TeiRerankResponseFactory
from api.tests.unit.infrastructure.http.model.factories import ModelHttpExchangeFactory, OriginalModelRequestFactory


class TestTeiRerankAdapter:
    def test_should_format_valid_rerank_original_request(self):
        # Arrange
        original_request = OriginalModelRequestFactory(rerank=True)
        method, url, model_name = HTTPMethod.POST, "https://test.com/v1/rerank", "test-model"
        adapter = TeiRerankAdapter()

        # Act
        result = adapter.format_request(original_request=original_request, method=method, url=url, model_name=model_name)

        # Assert
        assert result == ProviderFormattedRequest(
            method=method,
            url=url,
            body={
                "query": original_request.body["query"],
                "texts": original_request.body["documents"],
                "raw_scores": False,
                "return_text": False,
                "truncate": False,
                "truncation_direction": "right",
            },
        )

    def test_should_format_valid_rerank_original_response(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(rerank=True),
            formatted_request=TeiFormattedModelRequestFactory(rerank=True),
            original_response=ProviderOriginalResponse(
                data=TeiRerankResponseFactory(data=[{"index": 2, "score": 0.95}, {"index": 0, "score": 0.72}]), latency=10
            ),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = TeiRerankAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)
        # Assert
        assert result == ProviderFormattedResponse(
            data=Reranks(
                id=mock_request_id,
                model="openweight-rerank",
                results=[{"index": 2, "relevance_score": 0.95}, {"index": 0, "relevance_score": 0.72}],
                usage=mock_usage.model_dump(),
            )
        )


class TestTeiModelsAdapter:
    def test_should_format_valid_original_response(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            formatted_request=TeiFormattedModelRequestFactory(models=True),
            original_response=ProviderOriginalResponse(data=TeiModelsResponseFactory(model_id="tei-model-1234", max_context_length=8192)),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = TeiModelsAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=ModelsResponse(
                data=[
                    Model(
                        id="tei-model-1234",
                        created=0,
                        owned_by="tei",
                        max_context_length=8192,
                    )
                ]
            )
        )
