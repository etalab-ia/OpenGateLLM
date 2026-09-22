from http import HTTPMethod

from api.domain.provider.entities import ProviderEndpoint, ProviderMetrics
from api.infrastructure.http.adapters import HttpProviderAdapter


class MetricsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.METRICS
    TARGET_ENDPOINT_ROUTE = "/metrics"
    TARGET_ENDPOINT_METHOD = HTTPMethod.GET
    RESPONSE_TYPE = ProviderMetrics
