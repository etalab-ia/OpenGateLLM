from api.domain.provider.entities import ProviderModel, ProviderModels, ProviderRequest, ProviderResponse
from api.domain.router.entities import RouterType
from api.infrastructure.http._httpproviderresponse import HttpProviderResponse
from api.infrastructure.http.adapters.models import ModelsAdapter


class MistralModelsAdapter(ModelsAdapter):
    def to_provider_response(
        self,
        http_response: HttpProviderResponse,
        request: ProviderRequest,
    ) -> ProviderResponse:
        return ProviderResponse(
            data=ProviderModels(
                data=[
                    ProviderModel(
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_context_length"],
                        type=RouterType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in http_response.data.get("data", [])
                ]
            ),
        )
