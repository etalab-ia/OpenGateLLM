from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalResponse
from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.infrastructure.http.model.vllm.adapters import VllmModelsAdapter
from api.schemas.usage import Usage
from api.tests.integration.factories.vllm import VllmFormattedModelRequestFactory, VllmModelsResponseFactory
from api.tests.unit.infrastructure.http.model.factories import ModelHttpExchangeFactory, OriginalModelRequestFactory


class TestVllmModelsAdapter:
    def test_should_format_valid_original_response(self):
        # Arrange
        exchange = ModelHttpExchangeFactory(
            original_request=OriginalModelRequestFactory(models=True),
            formatted_request=VllmFormattedModelRequestFactory(models=True),
            original_response=ProviderOriginalResponse(data=VllmModelsResponseFactory(model_id="openai/gpt-oss-120b", max_context_length=131072)),
        )
        mock_request_id = "request-1234567890"
        mock_usage = Usage()
        adapter = VllmModelsAdapter()

        # Act
        result = adapter.format_response(exchange=exchange, request_id=mock_request_id, usage=mock_usage)

        # Assert
        assert result == ProviderFormattedResponse(
            data=ModelsResponse(
                data=[
                    Model(
                        id="openai/gpt-oss-120b",
                        created=1773657692,
                        owned_by="vllm",
                        max_context_length=131072,
                    )
                ]
            )
        )
