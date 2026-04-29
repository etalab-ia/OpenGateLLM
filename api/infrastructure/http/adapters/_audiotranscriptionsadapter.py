from contextvars import ContextVar
from http import HTTPMethod

from api.domain.audio.entities import AudioTranscription
from api.domain.provider.entities import ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.infrastructure.fastapi.context import RequestContext
from api.utils.variables import EndpointRoute

from ._endpointadapter import EndpointAdapter


class AudioTranscriptionsAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS
    TARGET_ENDPOINT_ROUTE = "/v1/audio/transcriptions"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    # REQUEST_TYPE = CreateAudioTranscriptionCommand
    RESPONSE_TYPE = AudioTranscription

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        request_context: ContextVar[RequestContext],
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        # @TODO: handle vtt, srt response formats
        if original_response.text is not None:
            return ProviderFormattedResponse(text=original_response.data["text"])

        formatted_response = ProviderFormattedResponse(data=self.RESPONSE_TYPE(**original_response.data))
        request_id = self._extract_request_id(original_response=original_response)
        request_context.get().id = request_id
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.form.model
        formatted_response.latency = original_response.latency
        usage = self._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)
        request_context.get().usage = usage
        formatted_response.data.usage = usage

        return formatted_response
