from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from api.domain.audio.entities import (
    AudioTranscriptions,
    AudioTranscriptionsResponseFormat,
    CreateAudioTranscriptionsFile,
    CreateAudioTranscriptionsForm,
)
from api.domain.audio.errors import AudioFileSizeLimitExceededError
from api.domain.model.entities import ModelType as RouterType
from api.domain.provider.entities import ProviderResponse
from api.domain.router.entities import RouterRateLimitState
from api.domain.usage import UsageRecorder
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, RouterFactory
from api.use_cases.audio import (
    CreateAudioTranscriptionsCommand,
    CreateAudioTranscriptionsJsonUseCaseSuccess,
    CreateAudioTranscriptionsTextUseCaseSuccess,
    CreateAudioTranscriptionsUseCase,
)
from api.utils.variables import EndpointRoute


@pytest.fixture
def model_tokenizer():
    tokenizer = MagicMock()
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    return tokenizer


@pytest.fixture
def usage_recorder():
    return create_autospec(UsageRecorder, instance=True, spec_set=True)


@pytest.fixture
def router():
    return RouterFactory(
        id=1,
        name="audio-router",
        type=RouterType.AUTOMATIC_SPEECH_RECOGNITION,
        providers=1,
    )


@pytest.fixture
def sample_transcriptions():
    return AudioTranscriptions(id="audio-1", text="hello world", model="audio-router")


@pytest.fixture
def admin_user():
    return AuthenticatedUserFactory(id=1, admin=True)


@pytest.fixture
def make_command():
    def _make(
        user,
        *,
        size: int = 10,
        response_format: AudioTranscriptionsResponseFormat = AudioTranscriptionsResponseFormat.JSON,
    ):
        return CreateAudioTranscriptionsCommand(
            payload=CreateAudioTranscriptionsForm(
                file=CreateAudioTranscriptionsFile(
                    name="speech.mp3",
                    file=b"audio-bytes",
                    content_type="audio/mpeg",
                    size=size,
                ),
                model="audio-router",
                language=None,
                prompt="transcribe this",
                response_format=response_format,
                temperature=0.0,
            ),
            authenticated_user=user,
        )

    return _make


@pytest.fixture
def use_case(model_tokenizer, usage_recorder) -> CreateAudioTranscriptionsUseCase:
    return CreateAudioTranscriptionsUseCase(
        model_environmental_impacts_computer=MagicMock(),
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=MagicMock(),
        provider_client=AsyncMock(),
        provider_load_balancer=AsyncMock(),
        provider_metrics_logger=AsyncMock(),
        provider_repository=AsyncMock(),
        router_rate_limiter=AsyncMock(),
        router_repository=AsyncMock(),
        usage_recorder=usage_recorder,
        audio_file_size_limit=None,
    )


class TestCreateAudioTranscriptionsUseCase:
    def test_should_use_automatic_speech_recognition_router_type(self):
        assert CreateAudioTranscriptionsUseCase.ROUTER_TYPE == RouterType.AUTOMATIC_SPEECH_RECOGNITION

    def test_should_use_audio_transcriptions_endpoint(self):
        assert CreateAudioTranscriptionsUseCase.ENDPOINT == EndpointRoute.AUDIO_TRANSCRIPTIONS


class TestCreateAudioTranscriptionsUseCaseExecute:
    @pytest.fixture(autouse=True)
    def mock_collaborator_methods(self, use_case, router, sample_transcriptions):
        formatted_response = ProviderResponse(id=sample_transcriptions.id, data=sample_transcriptions)
        use_case._resolve_router = AsyncMock(return_value=router)
        use_case._check_rate_limits = AsyncMock(return_value=RouterRateLimitState.admin_rate_limit_state())
        use_case._send_request = AsyncMock(return_value=formatted_response)

    @pytest.mark.asyncio
    async def test_should_return_file_size_limit_exceeded_error_when_file_is_too_large(self, use_case, make_command, admin_user):
        # Arrange
        use_case.audio_file_size_limit = 5
        command = make_command(admin_user, size=10)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result == AudioFileSizeLimitExceededError(size=10, expected_size=5)
        use_case._resolve_router.assert_not_awaited()
        use_case.model_tokenizer.compute_tokens.assert_not_called()
        use_case._check_rate_limits.assert_not_awaited()
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_call_parent_methods_and_return_json_success_when_formatted_response_has_data(
        self, use_case, make_command, admin_user, router, sample_transcriptions
    ):
        # Arrange
        command = make_command(admin_user)
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        use_case._check_rate_limits.return_value = rate_limit_state

        # Act
        result = await use_case.execute(command=command)

        # Assert
        use_case._resolve_router.assert_awaited_once_with(authenticated_user=admin_user, model_name_or_alias="audio-router")
        use_case.model_tokenizer.compute_tokens.assert_called_once_with(texts=["transcribe this"])
        use_case._check_rate_limits.assert_awaited_once_with(authenticated_user=admin_user, router=router, prompt_tokens=1)
        use_case._send_request.assert_awaited_once_with(router=router, prompt_tokens=1, payload=command.payload)
        assert isinstance(result, CreateAudioTranscriptionsJsonUseCaseSuccess)
        assert result.data is sample_transcriptions
        assert result.headers == rate_limit_state.build_limit_headers
        assert result.media_type == "application/json"

    @pytest.mark.asyncio
    async def test_should_return_text_success_when_formatted_response_has_no_data(self, use_case, make_command, admin_user):
        # Arrange
        command = make_command(admin_user, response_format=AudioTranscriptionsResponseFormat.TEXT)
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        use_case._check_rate_limits.return_value = rate_limit_state
        use_case._send_request.return_value = ProviderResponse(id="audio-1", text="hello world")

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateAudioTranscriptionsTextUseCaseSuccess)
        assert result.text == "hello world"
        assert result.headers == rate_limit_state.build_limit_headers
        assert result.media_type == "text/plain"
