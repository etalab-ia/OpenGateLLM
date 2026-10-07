import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from api.domain.key.entities import Key
from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import UsageRecorder
from api.infrastructure.fastapi._usagerecorder import _pending_saves

USER_ID = 42


@pytest.fixture
def mock_usage_repository():
    return create_autospec(UsageRepository, instance=True, spec_set=True)


@pytest.fixture
def recorder(mock_usage_repository) -> UsageRecorder:
    now = datetime.now(tz=UTC)

    return UsageRecorder.open(
        usage_repository=mock_usage_repository,
        request_id="3f2a",
        endpoint="/v1/chat/completions",
        user=AuthenticatedUserView(id=USER_ID, email="alice@example.com", name="Alice", organization_id=1, permissions=[], limits=[], expires=None),
        key=Key(id=7, name="my-key", user_id=USER_ID, value="sk-...", expires=None, created=now),
    )


def _usage(cost: float = 0.02) -> Usage:
    return Usage(prompt_tokens=7, completion_tokens=3, total_tokens=10, cost=cost, impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5))


async def _drain_saves() -> None:
    if _pending_saves:
        await asyncio.gather(*tuple(_pending_saves))


class TestOpen:
    def test_should_build_the_record_from_the_authenticated_request(self, recorder, mock_usage_repository):
        # Assert
        assert recorder.record.request_id == "3f2a"
        assert recorder.record.endpoint == "/v1/chat/completions"
        assert (recorder.record.user_id, recorder.record.user_email) == (USER_ID, "alice@example.com")
        assert (recorder.record.key_id, recorder.record.key_name) == (7, "my-key")
        mock_usage_repository.open_record.assert_called_once_with(recorder.record)

    def test_should_share_its_request_id_with_the_use_case(self, recorder):
        # Assert: the provider request and the usage record carry the same id as the X-Request-ID header
        assert recorder.get_request_id() == "3f2a"

    def test_should_measure_from_the_moment_the_record_was_opened(self, recorder):
        # Act
        elapsed = recorder.elapsed_ms(at=recorder.record.created + timedelta(milliseconds=250))

        # Assert
        assert elapsed == 250


class TestRecord:
    def test_should_keep_what_the_use_case_resolved(self, recorder):
        # Act
        recorder.record_router(router_id=3, router_name="my-router")
        recorder.record_provider(provider_id=8, provider_model_name="provider-model")
        recorder.record_usage(usage=_usage(), latency=250, ttft=50)

        # Assert
        assert (recorder.record.router_id, recorder.record.router_name) == (3, "my-router")
        assert (recorder.record.provider_id, recorder.record.provider_model_name) == (8, "provider-model")
        assert (recorder.record.latency, recorder.record.ttft) == (250, 50)
        assert recorder.record.usage.total_tokens == 10

    def test_should_leave_the_ttft_unset_when_the_response_was_not_streamed(self, recorder):
        # Act
        recorder.record_usage(usage=_usage(), latency=250)

        # Assert
        assert recorder.record.ttft is None


@pytest.mark.asyncio
class TestClose:
    async def test_should_stamp_the_answered_status_and_save_the_record(self, recorder, mock_usage_repository):
        # Arrange
        recorder.record_usage(usage=_usage(), latency=250)

        # Act
        recorder.close(status_code=200)
        await _drain_saves()

        # Assert
        assert (recorder.record.status, recorder.record.latency) == (200, 250)
        mock_usage_repository.save_record.assert_awaited_once_with(recorder.record)

    async def test_should_keep_how_long_a_failed_request_took_when_the_provider_was_never_reached(self, recorder):
        # Act: no use case recorded anything — what an incident needs is how long it took to fail
        recorder.close(status_code=503, error="NoAvailableProviderError")
        await _drain_saves()

        # Assert
        assert recorder.record.status == 503
        assert recorder.record.error == "NoAvailableProviderError"
        assert recorder.record.latency is not None

    async def test_should_save_the_record_once_only(self, recorder, mock_usage_repository):
        # Act
        recorder.close(status_code=200)
        recorder.close(status_code=500)
        await _drain_saves()

        # Assert
        assert recorder.record.status == 200
        mock_usage_repository.save_record.assert_awaited_once()
