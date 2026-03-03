from copy import deepcopy

import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import TeiModelHttpClient
from api.schemas.core.models import RequestContent
from api.schemas.rerank import RerankResult, Reranks
from api.tests.unit.infrastructure.http.factories import (
    FormattedRequestContentFactory,
    TeiFormattedRequestContentFactory,
    TeiModelsResponseFactory,
    TeiRerankResponseFactory,
)
from api.utils.variables import EndpointRoute


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


@pytest.fixture
def rerank_request_content():
    return FormattedRequestContentFactory(rerank=True)


@pytest.fixture
def tei_rerank_request_content(tei_model_http_client):
    return TeiFormattedRequestContentFactory(rerank=True, model=tei_model_http_client.model_name)


@pytest.fixture
def tei_models_request_content(tei_model_http_client):
    return TeiFormattedRequestContentFactory(models=True, model=tei_model_http_client.model_name)


@pytest.fixture
def tei_rerank_response_data(tei_rerank_request_content: TeiFormattedRequestContentFactory):
    return TeiRerankResponseFactory(request_content=tei_rerank_request_content, raw_scores=False, return_text=False)


@pytest.fixture
def tei_models_response_data():
    return TeiModelsResponseFactory(embedding=True)


class TestTeiModelHttpClient:
    @pytest.mark.asyncio
    async def test_should_format_rerank_request(self, tei_model_http_client, rerank_request_content):
        # Arrange
        request_content = rerank_request_content.model_copy(deep=True)

        # Act
        result = tei_model_http_client.format_rerank_request(request_content)

        # Assert
        assert result == RequestContent(
            method="POST",
            model=rerank_request_content.model,
            endpoint=EndpointRoute.RERANK,
            body={
                "query": rerank_request_content.body["query"],
                "texts": rerank_request_content.body["documents"],
                "raw_scores": False,
                "return_text": False,
                "truncate": False,
                "truncation_direction": "right",
            },
            form={},
            files={},
            additional_data={"top_n": rerank_request_content.body["top_n"]},
        )

    @pytest.mark.asyncio
    async def test_should_format_rerank_response_to_reranks_format(
        self,
        tei_model_http_client,
        tei_rerank_request_content,
        tei_rerank_response_data,
    ):
        # Arrange
        request_content = tei_rerank_request_content.model_copy(deep=True)
        response_data = deepcopy(tei_rerank_response_data)

        # Act
        result = tei_model_http_client.format_rerank_response(request_content=request_content, response_data=response_data)

        # Assert
        expected_results = [RerankResult(relevance_score=x["score"], index=x["index"]) for x in tei_rerank_response_data]
        expected_results = sorted(expected_results, key=lambda x: x.relevance_score, reverse=True)
        expected_results = expected_results[: tei_rerank_request_content.additional_data["top_n"]]

        assert result == Reranks(
            id=tei_rerank_request_content.additional_data["id"],
            model=tei_model_http_client.model_name,
            results=expected_results,
            usage=tei_rerank_request_content.additional_data["usage"],
        )

    @pytest.mark.asyncio
    async def test_should_format_response_to_models_format(self, tei_model_http_client, tei_models_request_content, tei_models_response_data):
        # Arrange
        request_content = tei_models_request_content.model_copy(deep=True)
        response_data = deepcopy(tei_models_response_data)

        # Act
        result = tei_model_http_client.format_response_to_models_response(request_content=request_content, response_data=response_data)

        # Assert
        assert result == ModelsResponse(
            data=[
                ModelResponse(
                    id=tei_models_response_data["model_id"],
                    created=0,
                    owned_by="tei",
                    max_context_length=tei_models_response_data["max_input_length"],
                )
            ]
        )
