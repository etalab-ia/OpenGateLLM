from http import HTTPMethod

from api.domain.rerank.entities import Rerank
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class RerankAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.RERANK
    TARGET_ENDPOINT_ROUTE = "/v1/rerank"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Rerank
