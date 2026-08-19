from dataclasses import dataclass

from api.domain.audio.entities import AudioTranscriptions, CreateAudioTranscriptionsBody
from api.domain.audio.errors import AudioFileSizeLimitExceededError
from api.domain.model.entities import ModelType as RouterType
from api.domain.provider.entities import ProviderFormattedResponse
from api.domain.router.entities import Router, RouterRateLimitState
from api.use_cases._providerrequestforwardingusecase import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseError
from api.utils.variables import EndpointRoute


class CreateAudioTranscriptionsCommand(ForwardingCommand[CreateAudioTranscriptionsBody]): ...


@dataclass
class CreateAudioTranscriptionsJsonUseCaseSuccess:
    data: AudioTranscriptions
    headers: dict[str, str]
    media_type: str


@dataclass
class CreateAudioTranscriptionsTextUseCaseSuccess:
    text: str
    headers: dict[str, str]
    media_type: str


AudioTranscriptionsUseCaseError = AudioFileSizeLimitExceededError | ProviderRequestForwardingUseCaseError

CreateAudioTranscriptionsUseCaseResult = (
    CreateAudioTranscriptionsJsonUseCaseSuccess | CreateAudioTranscriptionsTextUseCaseSuccess | AudioTranscriptionsUseCaseError
)


class CreateAudioTranscriptionsUseCase(ProviderRequestForwardingUseCase[CreateAudioTranscriptionsCommand, AudioTranscriptions]):
    ROUTER_TYPE = RouterType.AUTOMATIC_SPEECH_RECOGNITION
    ENDPOINT = EndpointRoute.AUDIO_TRANSCRIPTIONS

    async def execute(self, command: CreateAudioTranscriptionsCommand) -> CreateAudioTranscriptionsUseCaseResult:
        authenticated_user = command.authenticated_user

        if self.audio_file_size_limit is not None and command.file.size > self.audio_file_size_limit:
            return AudioFileSizeLimitExceededError(size=command.file.size, expected_size=self.audio_file_size_limit)

        result = await self._resolve_router(authenticated_user=authenticated_user, model_name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        prompt_tokens = self.model_tokenizer.compute_tokens(texts=command.get_prompts())

        result = await self._check_rate_limits(authenticated_user=authenticated_user, router=router, prompt_tokens=prompt_tokens)
        match result:
            case RouterRateLimitState() as rate_limit_state:
                pass
            case error:
                return error

        result = await self._send_request(router=router, body=command.body, prompt_tokens=prompt_tokens)
        match result:
            case ProviderFormattedResponse() as formatted_response:
                pass
            case error:
                return error

        if formatted_response.data:
            return CreateAudioTranscriptionsJsonUseCaseSuccess(
                data=formatted_response.data,
                headers=rate_limit_state.build_limit_headers,
                media_type=command.response_format.media_type,
            )
        else:
            return CreateAudioTranscriptionsTextUseCaseSuccess(
                text=formatted_response.text,
                headers=rate_limit_state.build_limit_headers,
                media_type=command.response_format.media_type,
            )
