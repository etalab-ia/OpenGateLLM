from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.http.adapters.models import ModelsAdapter


class TeiModelsAdapter(ModelsAdapter):
    TARGET_ENDPOINT_ROUTE = "/info"

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
        latency: int = 0,
    ) -> ProviderFormattedResponse:
        request_id = self._extract_request_id(original_response=original_response)
        return ProviderFormattedResponse(
            id=request_id,
            data=Models(
                data=[
                    Model(
                        id=original_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=original_response.data["max_input_length"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                ]
            ),
        )
