from http import HTTPMethod

from api.domain.provider.entities import ProviderEndpoint
from api.domain.rerank.entities import Rerank
from api.infrastructure.http.adapters import HttpProviderAdapter


class RerankAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.RERANK
    TARGET_ENDPOINT_ROUTE = "/v1/rerank"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Rerank
