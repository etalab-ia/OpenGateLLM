from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.http.adapters import ModelsAdapter, OcrAdapter, RerankAdapter


class VllmModelsAdapter(ModelsAdapter):
    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        return ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_model_len"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in original_response.data.get("data", [])
                ]
            ),
            metrics=original_response.metrics,
        )


class VllmOcrAdapter(OcrAdapter):
    TARGET_ENDPOINT_ROUTE = None


class VllmRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = "/v2/reranks"
