from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.infrastructure.http.adapters.models import ModelsAdapter


class MistralModelsAdapter(ModelsAdapter):
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
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_context_length"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in raw_response.data.get("data", [])
                ]
            ),
        )
