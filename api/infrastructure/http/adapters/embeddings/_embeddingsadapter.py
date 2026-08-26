from http import HTTPMethod

from pydantic import ValidationError

from api.domain.embeddings.entities import Embeddings
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class EmbeddingsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.EMBEDDINGS
    TARGET_ENDPOINT_ROUTE = "/v1/embeddings"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = Embeddings

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        request_id = self._extract_request_id(raw_response=raw_response)
        try:
            encoding_format = request.payload.encoding_format
            data = self.RESPONSE_TYPE._from_provider_response(
                raw_response.data,
                encoding_format=encoding_format,
                id=request_id,
                model=request.payload.model,
            )
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderResponse(id=request_id, data=data)
