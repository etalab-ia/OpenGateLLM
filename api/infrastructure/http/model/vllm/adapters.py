from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import Model, ModelsResponse
from api.infrastructure.http.model import ModelHttpClient, ModelHttpClientEndpoints
from api.infrastructure.http.model.adapters import ModelsAdapter
from api.infrastructure.http.model.exchanges import FormattedModelResponse, ModelHttpExchange
from api.schemas.usage import Usage
from api.utils.variables import EndpointRoute


class VllmModelsAdapter(ModelsAdapter):
    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        return FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    Model(
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
