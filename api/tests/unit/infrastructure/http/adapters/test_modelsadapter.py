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
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http.adapters._modelsadapter import ModelsAdapter
from api.tests.integration.factories.vllm import VllmModelsResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def provider():
    return ProviderFactory(type=ProviderType.OPENAI, url="https://provider.test", model_name="test-model")


@pytest.fixture
def request_context() -> ContextVar[RequestContext]:
    context = ContextVar("request_context")
    context.set(RequestContext())
    return context


@pytest.fixture
def models_adapter(provider) -> ModelsAdapter:
    return ModelsAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=provider)


class TestModelsAdapter:
    def test_should_use_v1_models_target_route(self, models_adapter: ModelsAdapter):
        # Assert
        assert models_adapter.TARGET_ENDPOINT_ROUTE == "/v1/models"
        assert models_adapter.TARGET_ENDPOINT_METHOD == HTTPMethod.GET
        assert models_adapter.SOURCE_ENDPOINT == EndpointRoute.MODELS

    def test_should_format_models_request_with_v1_models_route(self, models_adapter: ModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)

        # Act
        result = models_adapter.format_request(original_request)

        # Assert
        assert result == ProviderFormattedRequest(method=HTTPMethod.GET, url="https://provider.test/v1/models")

    def test_should_format_models_response_from_data_list(self, models_adapter: ModelsAdapter, request_context: ContextVar[RequestContext]):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)
        response = VllmModelsResponseFactory(model_id="openai/gpt-oss-120b", max_context_length=131072)
        print("##########################################")
        print(response)
        print("##########################################")
        original_response = ProviderOriginalResponse(data=response, metrics=ResponseMetrics(latency=10))

        # Act
        result = models_adapter.format_response(
            original_response=original_response,
            original_request=original_request,
            request_context=request_context,
        )

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

    def test_should_apply_defaults_for_missing_model_fields(self, models_adapter: ModelsAdapter, request_context: ContextVar[RequestContext]):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)
        response_data = VllmModelsResponseFactory(data=[{"id": "minimal-model"}])
        original_response = ProviderOriginalResponse(data=response_data, metrics=ResponseMetrics(latency=5))

        # Act
        result = models_adapter.format_response(
            original_response=original_response,
            original_request=original_request,
            request_context=request_context,
        )

        # Assert
        assert result.data.data == [
            Model(
                id="minimal-model",
                created=0,
                owned_by="unknown",
                max_context_length=None,
                type=ModelType.TEXT_GENERATION,
            )
        ]

    def test_should_return_zero_prompt_and_completion_tokens(self, models_adapter: ModelsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(endpoint=EndpointRoute.MODELS, body=None)

        # Act / Assert
        assert models_adapter.compute_prompt_tokens(original_request) == 0
        assert models_adapter.compute_completion_tokens(formatted_response=None) == 0
