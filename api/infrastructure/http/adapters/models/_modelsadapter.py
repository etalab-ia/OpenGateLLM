from http import HTTPMethod

from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class ModelsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.MODELS
    TARGET_ENDPOINT_ROUTE = "/v1/models"
    TARGET_ENDPOINT_METHOD = HTTPMethod.GET
    RESPONSE_TYPE = Model

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest:
        return ProviderFormattedRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE),
        )

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse:
        request_id = self._extract_request_id(original_response=original_response)
        return ProviderFormattedResponse(
            id=request_id,
            data=Models(
                data=[
                    Model(
                        id=model["id"],
                        aliases=model.get("aliases", []),
                        created=model.get("created", 0),
                        owned_by=model.get("owned_by", "unknown"),
                        max_context_length=model.get("max_context_length", None),
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in original_response.data["data"]
                ]
            ),
        )
