from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.infrastructure.http.adapters.models import ModelsAdapter


class TeiModelsAdapter(ModelsAdapter):
    TARGET_ENDPOINT_ROUTE = "/info"

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse:
        request_id = self._extract_request_id(raw_response=raw_response)
        return ProviderResponse(
            id=request_id,
            data=Models(
                data=[
                    Model(
                        id=raw_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=raw_response.data["max_input_length"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                ]
            ),
        )
