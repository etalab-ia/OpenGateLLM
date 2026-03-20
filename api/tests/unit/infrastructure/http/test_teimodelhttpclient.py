import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import FormattedModelRequest, FormattedModelResponse, TeiModelHttpClient
from api.schemas.rerank import Reranks
from api.schemas.usage import Usage
from api.tests.unit.infrastructure.http.factories.common import HttpModelExchangeFactory, OriginalModelRequestFactory
from api.tests.unit.infrastructure.http.factories.tei import TeiFormattedModelRequestFactory, TeiOriginalResponseFactory


@pytest.fixture
def tei_model_http_client():
    return TeiModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


class TestTeiModelHttpClient:
    def test_should_format_valid_rerank_original_request(self, tei_model_http_client):
        # Arrange
        exchange = HttpModelExchangeFactory(original_request=OriginalModelRequestFactory(rerank=True))

        # Act
        result = tei_model_http_client.format_rerank_request(exchange=exchange)

        # Assert
        assert result.formatted_request == FormattedModelRequest(
            method="POST",
            endpoint="/rerank",
            body={
                "query": exchange.original_request.body["query"],
                "texts": exchange.original_request.body["documents"],
                "raw_scores": False,
                "return_text": False,
                "truncate": False,
                "truncation_direction": "right",
            },
        )

    def test_should_format_valid_rerank_original_response(self, tei_model_http_client, mocker):
        # Arrange
        exchange = HttpModelExchangeFactory(
            original_request=OriginalModelRequestFactory(rerank=True),
            formatted_request=TeiFormattedModelRequestFactory(rerank=True),
            original_response=TeiOriginalResponseFactory(rerank=True),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        mocker.patch.object(tei_model_http_client, "_get_request_id", return_value=mock_request_id)
        mocker.patch.object(tei_model_http_client, "_get_usage", return_value=mock_usage)

        # Act
        result = tei_model_http_client.format_response_to_rerank_response(exchange=exchange)

        # Assert
        assert result.formatted_response == FormattedModelResponse(
            data=Reranks(
                id=mock_request_id,
                model=exchange.original_request.body["model"],
                results=[{"index": 2, "relevance_score": 0.95}, {"index": 0, "relevance_score": 0.72}],
                usage=mock_usage.model_dump(),
            )
        )

    def test_should_format_valid_models_original_response(self, tei_model_http_client):
        # Arrange
        exchange = HttpModelExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            formatted_request=TeiFormattedModelRequestFactory(models=True),
            original_response=TeiOriginalResponseFactory(models=True),
        )

        # Act
        result = tei_model_http_client.format_response_to_models_response(exchange=exchange)

        # Assert
        assert result.formatted_response == FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id=exchange.original_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=8192,
                    )
                ]
            )
        )
