from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.schemas.usage import Usage
from api.utils.variables import EndpointRoute

from ._endpoint_adapters import ModelsAdapter
from ._exchanges import FormattedModelResponse, ModelHttpExchange
from ._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints


class VllmModelsAdapter(ModelsAdapter):
    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        return FormattedModelResponse(
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


class VllmModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(rerank=(HTTPMethod.POST, "/v2/rerank"))
    TYPE = ProviderType.VLLM

    def _build_adapters(self):
        adapters = super()._build_adapters()
        adapters[EndpointRoute.MODELS] = VllmModelsAdapter()
        return adapters
