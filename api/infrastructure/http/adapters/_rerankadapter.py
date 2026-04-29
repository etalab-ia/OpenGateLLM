from http import HTTPMethod

from api.domain.provider.entities import ProviderFormattedResponse
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.infrastructure.http.adapters._endpointadapter import EndpointAdapter
from api.utils.variables import EndpointRoute


class RerankAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.RERANK
    TARGET_ENDPOINT_ROUTE = "/v1/rerank"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Rerank
    REQUEST_TYPE = CreateRerankBody

    def compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        return 0
