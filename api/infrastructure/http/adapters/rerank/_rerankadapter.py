from http import HTTPMethod

from api.domain.provider.entities import ProviderFormattedResponse
from api.domain.rerank.entities import Rerank
from api.infrastructure.http.adapters._baseadapter import BaseAdapter
from api.utils.variables import EndpointRoute


class RerankAdapter(BaseAdapter):
    SOURCE_ENDPOINT = EndpointRoute.RERANK
    TARGET_ENDPOINT_ROUTE = "/v1/rerank"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Rerank

    def _compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        return 0
