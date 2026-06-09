from http import HTTPMethod

from api.domain.embeddings.entities import Embeddings
from api.domain.provider.entities import ProviderFormattedResponse
from api.infrastructure.http.adapters._baseadapter import BaseAdapter
from api.utils.variables import EndpointRoute


class EmbeddingsAdapter(BaseAdapter):
    SOURCE_ENDPOINT = EndpointRoute.EMBEDDINGS
    TARGET_ENDPOINT_ROUTE = "/v1/embeddings"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Embeddings

    def _compute_completion_tokens(self, formatted_response: ProviderFormattedResponse) -> int:
        return 0
