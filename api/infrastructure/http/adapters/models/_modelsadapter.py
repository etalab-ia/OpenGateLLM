from http import HTTPMethod

from api.domain.model.entities import Model, Models
from api.domain.provider.entities import ProviderRequest, ProviderResponse
from api.domain.router.entities import RouterType
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
from api.infrastructure.http._httpproviderresponse import HttpProviderResponse
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class ModelsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.MODELS
    TARGET_ENDPOINT_ROUTE = "/v1/models"
    TARGET_ENDPOINT_METHOD = HTTPMethod.GET
    RESPONSE_TYPE = Model

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest:
        return HttpProviderRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE),
        )

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
                        id=model["id"],
                        aliases=model.get("aliases", []),
                        created=model.get("created", 0),
                        owned_by=model.get("owned_by", "unknown"),
                        max_context_length=model.get("max_context_length", None),
                        type=RouterType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in http_response.data["data"]
                ]
            ),
        )
