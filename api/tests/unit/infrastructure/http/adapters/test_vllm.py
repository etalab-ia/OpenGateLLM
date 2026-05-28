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
from api.infrastructure.http.adapters.vllm import VllmModelsAdapter, VllmOcrAdapter, VllmRerankAdapter
from api.tests.integration.factories.vllm import VllmModelsResponseFactory, VllmRerankResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test/vllm-model")


@pytest.fixture
def vllm_models_adapter(vllm_provider) -> VllmModelsAdapter:
    return VllmModelsAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=vllm_provider)


@pytest.fixture
def vllm_rerank_adapter(vllm_provider) -> VllmRerankAdapter:
    return VllmRerankAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=vllm_provider)


class TestVllmModelsAdapter:
    def test_should_format_models_request_with_v1_models_route(self, vllm_models_adapter: VllmModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)

        # Act
        result = vllm_models_adapter.format_request(original_request)

        # Assert
        assert result == ProviderFormattedRequest(method=HTTPMethod.GET, url="https://vllm.test/v1/models")

    def test_should_format_models_response_using_max_model_len(self, vllm_models_adapter: VllmModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)
        response_data = VllmModelsResponseFactory(model_id="openai/gpt-oss-120b", max_context_length=131072)
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        result = vllm_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert result == ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id="openai/gpt-oss-120b",
                        created=1773657692,
                        owned_by="vllm",
                        max_context_length=131072,
                        type=ModelType.TEXT_GENERATION,
                    )
                ]
            ),
            metrics=ResponseMetrics(latency=10),
        )


class TestVllmOcrAdapter:
    def test_should_have_no_target_endpoint_route(self, vllm_provider):
        # Arrange
        adapter = VllmOcrAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=vllm_provider)

        # Assert
        assert adapter.TARGET_ENDPOINT_ROUTE is None


class TestVllmRerankAdapter:
    def test_should_use_v2_reranks_target_route(self, vllm_rerank_adapter: VllmRerankAdapter):
        # Assert
        assert vllm_rerank_adapter.TARGET_ENDPOINT_ROUTE == "/v2/reranks"

    def test_should_format_rerank_request_with_v2_reranks_route(self, vllm_rerank_adapter: VllmRerankAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = vllm_rerank_adapter.format_request(original_request)

        # Assert
        assert result.method == HTTPMethod.POST
        assert result.url == "https://vllm.test/v2/reranks"
        assert result.body["model"] == original_request.body.model
        assert result.body["query"] == original_request.body.query
        assert result.body["documents"] == original_request.body.documents
        assert result.body["top_n"] == original_request.body.top_n

    def test_should_format_rerank_response(self, vllm_rerank_adapter: VllmRerankAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)
        response_data = {**VllmRerankResponseFactory(count=3), "model": original_request.body.model}
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=10))

        # Act
        result = vllm_rerank_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.data == Rerank(
            id=response_data["id"],
            model=original_request.body.model,
            results=[RerankResult(index=r["index"], relevance_score=r["relevance_score"]) for r in response_data["results"]],
        )
        assert result.data.usage.total_tokens == 0
        assert result.metrics == ResponseMetrics(latency=10)
