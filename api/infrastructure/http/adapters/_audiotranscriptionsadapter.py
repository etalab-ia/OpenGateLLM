from http import HTTPMethod

from api.domain.audio.entities import AudioTranscription
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class AudioTranscriptionsAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS
    TARGET_ENDPOINT_ROUTE = "/v1/audio/transcriptions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    RESPONSE_TYPE = AudioTranscription

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        prompt_tokens: int = 0,
        latency: int = 0,
    ) -> ProviderFormattedResponse:
        if original_response.text is not None:
            return ProviderFormattedResponse(text=original_response.text)

        formatted_response = ProviderFormattedResponse(data=self.RESPONSE_TYPE(**original_response.data))
        request_id = self._extract_request_id(original_response=original_response)
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.form.model

        completion_tokens = self._compute_completion_tokens(formatted_response=formatted_response)
        usage = self._compute_usage(completion_tokens=completion_tokens, prompt_tokens=prompt_tokens, latency=latency)
        formatted_response.data.usage = usage

        return formatted_response
