from http import HTTPMethod

from api.domain.audio.entities import AudioTranscriptions
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.utils.variables import EndpointRoute


class AudioTranscriptionsAdapter(HttpProviderAdapter):
    SOURCE_ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS
    TARGET_ENDPOINT_ROUTE = "/v1/audio/transcriptions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = AudioTranscriptions

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
    ) -> ProviderFormattedResponse:
        if original_response.text is not None:
            return ProviderFormattedResponse(text=original_response.text)

        formatted_response = ProviderFormattedResponse(data=self.RESPONSE_TYPE(**original_response.data))
        request_id = self._extract_request_id(original_response=original_response)
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.form.model

        return formatted_response
