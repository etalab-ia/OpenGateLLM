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
        request_id = self._extract_request_id(original_response=original_response)
        try:
            encoding_format = original_request.payload.encoding_format
            data = self.RESPONSE_TYPE._from_provider_response(
                original_response.data,
                encoding_format=encoding_format,
                id=request_id,
                model=original_request.payload.model,
            )
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderFormattedResponse(id=request_id, data=data)
