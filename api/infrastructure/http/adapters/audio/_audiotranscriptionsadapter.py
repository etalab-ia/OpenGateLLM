from http import HTTPMethod

from pydantic import ValidationError

from api.domain.audio.entities import AudioTranscriptions
from api.domain.provider.entities import ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
from api.infrastructure.http._httpproviderresponse import HttpProviderResponse
from api.infrastructure.http.adapters import HttpProviderAdapter


class AudioTranscriptionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = ProviderEndpoint.AUDIO_TRANSCRIPTIONS
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

    def to_provider_response(
        self,
        http_response: HttpProviderResponse,
        request: ProviderRequest,
    ) -> ProviderResponse | ProviderAdapterValidationResponseError:
        if http_response.text is not None:
            return ProviderResponse(text=http_response.text)

        try:
            data = self.RESPONSE_TYPE.model_validate({"id": request.id, "model": request.payload.model, **http_response.data})
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderResponse(data=data)
