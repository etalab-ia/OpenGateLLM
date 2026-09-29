from dataclasses import dataclass

from api.domain.audio.entities import AudioTranscriptions, AudioTranscriptionsResponseFormat, CreateAudioTranscriptionsForm
from api.domain.audio.errors import AudioFileSizeLimitExceededError
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderQoS, ProviderRepository
from api.domain.provider.entities import ProviderEndpoint, ProviderResponse
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.usage import UsageContext, UsageRepository
from api.use_cases._providerrequestforwardingusecase import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseError


class CreateAudioTranscriptionsCommand(ForwardingCommand[CreateAudioTranscriptionsForm]):
    @property
    def file_size(self) -> int:
        return self.payload.file.size

    @property
    def media_type(self) -> AudioTranscriptionsResponseFormat:
        return self.payload.response_format.media_type


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


type AudioTranscriptionsUseCaseError = AudioFileSizeLimitExceededError | ProviderRequestForwardingUseCaseError

type CreateAudioTranscriptionsUseCaseResult = (
    CreateAudioTranscriptionsJsonUseCaseSuccess | CreateAudioTranscriptionsTextUseCaseSuccess | AudioTranscriptionsUseCaseError
)


class CreateAudioTranscriptionsUseCase(ProviderRequestForwardingUseCase[CreateAudioTranscriptionsCommand, CreateAudioTranscriptionsUseCaseResult]):
    ROUTER_TYPE = RouterType.AUTOMATIC_SPEECH_RECOGNITION
    ENDPOINT = ProviderEndpoint.AUDIO_TRANSCRIPTIONS

    def __init__(
        self,
        model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer,
        model_tokenizer: ModelTokenizer,
        provider_client: ProviderClient,
        provider_qos: ProviderQoS,
        provider_repository: ProviderRepository,
        router_rate_limiter: RouterRateLimiter,
        router_repository: RouterRepository,
        usage_context: UsageContext,
        usage_repository: UsageRepository,
        audio_file_size_limit: int | None = None,
    ) -> None:
        super().__init__(
            model_environmental_impacts_computer=model_environmental_impacts_computer,
            model_tokenizer=model_tokenizer,
            provider_client=provider_client,
            provider_qos=provider_qos,
            provider_repository=provider_repository,
            router_rate_limiter=router_rate_limiter,
            router_repository=router_repository,
            usage_context=usage_context,
            usage_repository=usage_repository,
        )
        self.audio_file_size_limit = audio_file_size_limit

    def _check_command(self, command: CreateAudioTranscriptionsCommand) -> AudioFileSizeLimitExceededError | None:
        if self.audio_file_size_limit is not None and command.file_size > self.audio_file_size_limit:
            return AudioFileSizeLimitExceededError(size=command.file_size, expected_size=self.audio_file_size_limit)

        return None

    def _build_success(
        self,
        command: CreateAudioTranscriptionsCommand,
        response: ProviderResponse,
        headers: dict[str, str],
    ) -> CreateAudioTranscriptionsJsonUseCaseSuccess | CreateAudioTranscriptionsTextUseCaseSuccess:
        if response.data:
            return CreateAudioTranscriptionsJsonUseCaseSuccess(data=response.data, headers=headers, media_type=command.media_type)

        return CreateAudioTranscriptionsTextUseCaseSuccess(text=response.text, headers=headers, media_type=command.media_type)
