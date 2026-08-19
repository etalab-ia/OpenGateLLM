from http import HTTPMethod

from pydantic import ValidationError

from api.domain.audio.entities import AudioTranscriptions
from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class AudioTranscriptionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS
    TARGET_ENDPOINT_ROUTE = "/v1/audio/transcriptions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = AudioTranscriptions

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        formatted_request = ProviderFormattedRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            form=original_request.payload.model_dump(exclude_none=True, exclude={"file"}),
            files={"file": (original_request.payload.file.name, original_request.payload.file.file, original_request.payload.file.content_type)},
        )
        formatted_request.form["model"] = self.provider.model_name

        return formatted_request

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse | ProviderAdapterValidationResponseError:
        request_id = self._extract_request_id(original_response=original_response)
        if original_response.text is not None:
            return ProviderFormattedResponse(id=request_id, text=original_response.text)

        try:
            data = self.RESPONSE_TYPE.model_validate({"id": request_id, "model": original_request.payload.model, **original_response.data})
        except ValidationError as e:
            return ProviderAdapterValidationResponseError(provider_type=self.provider.type, errors=e.errors())

        return ProviderFormattedResponse(id=request_id, data=data)
