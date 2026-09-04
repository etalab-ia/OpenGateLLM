from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_audio_transcriptions_use_case_factory
from api.domain.audio.errors import AudioFileSizeLimitExceededError
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import HostingZone, ProviderType
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.role.entities import LimitType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.conftest import override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_audio_transcriptions_responses
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.vllm import VllmAudioTranscriptionsResponseFactory
from api.use_cases.audio import CreateAudioTranscriptionsTextUseCaseSuccess
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}"

DEFAULT_MODEL_NAME = "audio-router"
AUDIO_BYTES = b"fake-mp3-bytes"
SAMPLE_VALIDATION_ERRORS = [{"type": "missing", "loc": ["file"], "msg": "Field required", "input": {}}]


def _valid_files() -> dict:
    return {"file": ("speech.mp3", AUDIO_BYTES, "audio/mpeg")}


def _valid_data(**overrides) -> dict:
    data = {"model": DEFAULT_MODEL_NAME}
    data.update(overrides)
    return data


@pytest.mark.asyncio(loop_scope="session")
class TestCreateAudioTranscriptions:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda text: [0] * 10 if text else []  # default prompt is empty
        with override_global_context(redis_pool=test_redis_pool, _tokenizer=mock_tokenizer):
            yield

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_audio_key", user=self.router_owner)
        RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.AUTOMATIC_SPEECH_RECOGNITION,
            providers=1,
            providers__type=ProviderType.VLLM,
            providers__url=DEFAULT_PROVIDER_URL,
            providers__model_hosting_zone=HostingZone.FRA,  # pin to an ecologits-resolvable zone (impacts now computed from transcription tokens)
        )
        await db_session.flush()

        mock_audio_transcriptions_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmAudioTranscriptionsResponseFactory(),
            status_code=VllmAudioTranscriptionsResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            files=_valid_files(),
            data=_valid_data(),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["model"] == DEFAULT_MODEL_NAME
        assert "id" in data
        assert "text" in data
        assert data["usage"]["prompt_tokens"] == 0
        assert data["usage"]["completion_tokens"] == 10  # tokens of the transcription (mock tokenizer: 10 per non-empty text)

    @respx.mock
    async def test_omitted_optional_fields_are_excluded_from_provider_body(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_audio_exclude_none_key", user=self.router_owner)
        RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.AUTOMATIC_SPEECH_RECOGNITION,
            providers=1,
            providers__type=ProviderType.VLLM,
            providers__url=DEFAULT_PROVIDER_URL,
            providers__model_hosting_zone=HostingZone.FRA,
        )
        await db_session.flush()

        route = mock_audio_transcriptions_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmAudioTranscriptionsResponseFactory(),
            status_code=VllmAudioTranscriptionsResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            files=_valid_files(),
            data=_valid_data(),
        )

        assert response.status_code == 200, response.text
        provider_body = route.calls[0].request.content
        assert b'name="language"' not in provider_body

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(name=DEFAULT_MODEL_NAME),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                RouterHasNoProvidersError(id=1),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                UserHasNoAccessToRouterError(id=1),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                UserHasInsufficientBudgetError(),
                400,
                "Insufficient budget.",
            ),
            (
                AudioFileSizeLimitExceededError(size=100, expected_size=50),
                413,
                "File size limit exceeded. Expected: 50 Bytes. Actual: 100 Bytes.",
            ),
            (
                RouterHasWrongTypeError(id=1, actual_type=RouterType.TEXT_GENERATION, expected_type=RouterType.AUTOMATIC_SPEECH_RECOGNITION),
                422,
                "Model has wrong type. Expected: automatic-speech-recognition. Actual: text-generation.",
            ),
            (
                NoAvailableProviderError(router_id=1),
                503,
                "Model is too busy, please try again later.",
            ),
            (
                TooBusyModelError(status_code=503, detail="provider busy"),
                503,
                "Model is too busy, please try again later.",
            ),
            (
                RouterRateLimitExceededError(id=1, limit_type=LimitType.RPM, headers={}),
                429,
                "Request limit per minute exceeded.",
            ),
            (
                StatusCodeModelError(status_code=400, detail="bad request"),
                400,
                "bad request",
            ),
            (
                UnknownModelError(status_code=500, detail="upstream failure"),
                500,
                "upstream failure",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_audio_transcriptions_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            files=_valid_files(),
            data=_valid_data(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "use_case_result",
        [
            ProviderAdapterValidationRequestError(provider_type=ProviderType.VLLM, errors=SAMPLE_VALIDATION_ERRORS),
            ProviderAdapterValidationResponseError(provider_type=ProviderType.VLLM, errors=SAMPLE_VALIDATION_ERRORS),
        ],
    )
    async def test_adapter_validation_error_returns_422_with_errors(self, client: AsyncClient, app, use_case_result):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_audio_transcriptions_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            files=_valid_files(),
            data=_valid_data(),
        )

        assert response.status_code == 422
        assert response.json().get("detail") == SAMPLE_VALIDATION_ERRORS

    async def test_text_success_returns_plain_text(self, client: AsyncClient, app):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = CreateAudioTranscriptionsTextUseCaseSuccess(
            text="hello world",
            headers={},
            media_type="text/plain",
        )
        app.dependency_overrides[create_audio_transcriptions_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            files=_valid_files(),
            data=_valid_data(response_format="text"),
        )

        assert response.status_code == 200
        assert response.text == "hello world"
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, files=_valid_files(), data=_valid_data())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
