import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import FormattedModelResponse, VllmModelHttpClient
from api.tests.unit.infrastructure.http.factories.common import ModelHttpExchangeFactory, OriginalModelRequestFactory
from api.tests.unit.infrastructure.http.factories.vllm import VllmFormattedModelRequestFactory, VllmOriginalResponseFactory


@pytest.fixture
def vllm_model_http_client() -> VllmModelHttpClient:
    return VllmModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="vllm-test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


class TestVllmModelHttpClient:
    def test_should_format_valid_models_original_response(self, vllm_model_http_client):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            formatted_request=VllmFormattedModelRequestFactory(models=True),
            original_response=VllmOriginalResponseFactory(models=True),
        )

        # Act
        result = vllm_model_http_client.format_response_to_models_response(exchange=exchange)

        # Assert
        assert result == FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id="openai/gpt-oss-120b",
                        created=1773657692,
                        owned_by="vllm",
                        max_context_length=131072,
                    )
                ]
            )
        )
