from http import HTTPMethod

from pydantic import ValidationError

from api.domain.audio.entities import AudioTranscriptions
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.infrastructure.http import HttpProviderRequest
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class AudioTranscriptionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS
    TARGET_ENDPOINT_ROUTE = "/v1/audio/transcriptions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = AudioTranscriptions

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        http_request = HttpProviderRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            form=request.payload.model_dump(exclude_none=True, exclude={"file"}),
            files={"file": (request.payload.file.name, request.payload.file.file, request.payload.file.content_type)},
        )
        http_request.form["model"] = self.provider.model_name

        return http_request

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        request_id = self._extract_request_id(raw_response=raw_response)
        if raw_response.text is not None:
            return ProviderResponse(id=request_id, text=raw_response.text)

        try:
            data = self.RESPONSE_TYPE.model_validate({"id": request_id, "model": request.payload.model, **raw_response.data})
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderResponse(id=request_id, data=data)
