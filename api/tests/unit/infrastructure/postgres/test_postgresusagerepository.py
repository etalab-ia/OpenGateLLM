from datetime import UTC, datetime
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import BackgroundTasks
import pytest

from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.postgres import PostgresUsageRepository
from api.sql.models import Usage as UsageTable
from api.utils.variables import EndpointRoute

IDENTITY = {
    "router_id": 3,
    "router_name": "chat-router",
    "user_email": "alice@example.com",
    "key_id": 7,
    "key_name": "my-key",
}


def _start_record(recorder, **overrides):
    return recorder.start_record(
        endpoint=EndpointRoute.CHAT_COMPLETIONS,
        model="chat-router",
        user_id=42,
        **IDENTITY,
        **overrides,
    )


def _usage() -> Usage:
    return Usage(
        prompt_tokens=3,
        completion_tokens=5,
        total_tokens=8,
        prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
        cost=0.01,
        impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
    )


@pytest.fixture
def mock_postgres_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def postgres_session_provider(mock_postgres_session):
    async def provider():
        yield mock_postgres_session

    return provider


@pytest.fixture
def background_tasks():
    return BackgroundTasks()


@pytest.fixture
def recorder(background_tasks, postgres_session_provider):
    return PostgresUsageRepository(background_tasks=background_tasks, postgres_session_provider=postgres_session_provider)


class TestPostgresUsageRepositoryRecording:
    def test_should_return_a_request_id(self, recorder):
        # Act
        request_id = _start_record(recorder)

        # Assert
        assert len(request_id) == 32

    def test_should_store_identity_on_the_row(self, recorder):
        # Act
        _start_record(recorder)

        # Assert
        row = recorder._row
        assert row.endpoint == "/v1/chat/completions"
        assert row.method == HTTPMethod.POST
        assert row.user_id == 42
        assert row.user_email == "alice@example.com"
        assert row.token_id == 7
        assert row.token_name == "my-key"
        assert row.router_id == 3
        assert row.router_name == "chat-router"
        assert row.created.tzinfo is UTC
        assert row.status is None

    def test_should_copy_usage_onto_the_row(self, recorder):
        # Arrange
        _start_record(recorder)

        # Act
        recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")

        # Assert
        row = recorder._row
        assert row.provider_id == 9
        assert row.provider_model_name == "vllm-model"
        assert row.prompt_tokens == 3
        assert row.completion_tokens == 5
        assert row.total_tokens == 8
        assert row.cost == 0.01
        assert row.kwh == 1.5
        assert row.kgco2eq == 2.5
        assert row.status == 200

    def test_should_set_latency_from_start_time(self, recorder):
        # Arrange
        start = datetime(2026, 9, 21, 10, 0, 0, tzinfo=UTC)
        end = datetime(2026, 9, 21, 10, 0, 0, 250000, tzinfo=UTC)

        # Act
        with patch("api.infrastructure.postgres._postgresusagerepository.datetime") as mock_datetime:
            mock_datetime.now.side_effect = [start, end]
            _start_record(recorder)
            recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")

        # Assert
        assert recorder._row.latency == 250
        assert recorder._row.ttft is None

    def test_should_set_ttft_from_first_token_at(self, recorder):
        # Arrange
        start = datetime(2026, 9, 21, 10, 0, 0, tzinfo=UTC)
        first_token_at = datetime(2026, 9, 21, 10, 0, 0, 50000, tzinfo=UTC)
        end = datetime(2026, 9, 21, 10, 0, 0, 250000, tzinfo=UTC)

        # Act
        with patch("api.infrastructure.postgres._postgresusagerepository.datetime") as mock_datetime:
            mock_datetime.now.side_effect = [start, end]
            _start_record(recorder)
            recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model", first_token_at=first_token_at)

        # Assert
        assert recorder._row.ttft == 50
        assert recorder._row.latency == 250

    def test_should_not_update_when_start_was_not_called(self, recorder):
        # Act / Assert
        recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")

    def test_should_not_fail_when_start_was_not_called(self, recorder):
        # Act / Assert
        recorder.fail_record(message="TooBusyModelError")

    def test_should_schedule_persist_on_end_record(self, recorder, background_tasks):
        # Arrange
        _start_record(recorder)
        recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")

        # Act
        recorder.end_record()

        # Assert
        assert len(background_tasks.tasks) == 1
        assert recorder._row is None

    def test_should_not_schedule_persist_when_start_was_not_called(self, recorder, background_tasks):
        # Act
        recorder.end_record()

        # Assert
        assert background_tasks.tasks == []

    @pytest.mark.asyncio
    async def test_should_persist_the_row(self, recorder, background_tasks, mock_postgres_session):
        # Arrange
        _start_record(recorder)
        recorder.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")
        recorder.end_record()

        # Act
        await background_tasks()

        # Assert
        mock_postgres_session.add.assert_called_once()
        row = mock_postgres_session.add.call_args.args[0]
        assert isinstance(row, UsageTable)
        assert row.user_id == 42
        assert row.prompt_tokens == 3
        assert row.status == 200
        mock_postgres_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_swallow_persist_errors(self, recorder, background_tasks, mock_postgres_session):
        # Arrange
        mock_postgres_session.commit.side_effect = RuntimeError("db down")
        _start_record(recorder)
        recorder.end_record()

        # Act / Assert
        await background_tasks()
        mock_postgres_session.rollback.assert_awaited_once()
