from http import HTTPMethod

from api.domain.provider.entities import ProviderMetrics
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class MetricsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.METRICS
    TARGET_ENDPOINT_ROUTE = "/metrics"
    TARGET_ENDPOINT_METHOD = HTTPMethod.GET
    RESPONSE_TYPE = ProviderMetrics
