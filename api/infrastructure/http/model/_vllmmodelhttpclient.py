from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse

from ._modelhttpclient import FormattedModelResponse, ModelHttpClient, ModelHttpClientEndpoints, ModelHttpExchange


class VllmModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(rerank=(HTTPMethod.POST, "/v2/rerank"))
    TYPE = ProviderType.VLLM

    # response formatting
    def format_response_to_models_response(self, exchange: ModelHttpExchange) -> FormattedModelResponse:
        formatted_response = FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_model_len"],
                    )
                    for model in exchange.original_response.data.get("data", [])
                ]
            )
        )

        return formatted_response
