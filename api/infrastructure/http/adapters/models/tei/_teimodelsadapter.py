from api.domain.model.entities import Model, Models
from api.domain.provider.entities import ProviderRequest, ProviderResponse
from api.domain.router.entities import RouterType
from api.infrastructure.http._httpproviderresponse import HttpProviderResponse
from api.infrastructure.http.adapters.models import ModelsAdapter


class TeiModelsAdapter(ModelsAdapter):
    TARGET_ENDPOINT_ROUTE = "/info"

    def to_provider_response(
        self,
        http_response: HttpProviderResponse,
        request: ProviderRequest,
    ) -> ProviderResponse:
        request_id = self._extract_request_id(http_response=http_response)
        return ProviderResponse(
            id=request_id,
            data=Models(
                data=[
                    Model(
                        id=http_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=http_response.data["max_input_length"],
                        type=RouterType.TEXT_GENERATION,  # dummy value, not used
                    )
                ]
            ),
        )
