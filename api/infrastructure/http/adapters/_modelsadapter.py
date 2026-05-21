from contextvars import ContextVar
from http import HTTPMethod

from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.fastapi.context import RequestContext
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class ModelsAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.MODELS
    TARGET_ENDPOINT_ROUTE = "/v1/models"
    TARGET_ENDPOINT_METHOD = HTTPMethod.GET
    REQUEST_TYPE = None
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
        request_context: ContextVar[RequestContext],
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        return ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id=model["id"],
                        created=model.get("created", 0),
                        owned_by=model.get("owned_by", "unknown"),
                        max_context_length=model.get("max_context_length", None),
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in original_response.data["data"]
                ]
            ),
            latency=original_response.latency,
        )

    def compute_prompt_tokens(self, original_request: ProviderOriginalRequest) -> int:
        return 0

    def compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        return 0
