from http import HTTPMethod

from pydantic import ValidationError

from api.domain.embeddings.entities import Embeddings
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class EmbeddingsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.EMBEDDINGS
    TARGET_ENDPOINT_ROUTE = "/v1/embeddings"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Embeddings

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:

        try:
            encoding_format = original_request.body.encoding_format
            embeddings = self.RESPONSE_TYPE._from_provider_response(original_response.data, encoding_format=encoding_format)
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        embeddings.id = self._extract_request_id(original_response=original_response)
        if original_request.body is not None and hasattr(original_request.body, "model"):
            embeddings.model = original_request.body.model

        return ProviderFormattedResponse(data=embeddings)
