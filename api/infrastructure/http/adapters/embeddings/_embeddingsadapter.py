from http import HTTPMethod

from api.domain.embeddings.entities import Embeddings
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class EmbeddingsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.EMBEDDINGS
    TARGET_ENDPOINT_ROUTE = "/v1/embeddings"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Embeddings
