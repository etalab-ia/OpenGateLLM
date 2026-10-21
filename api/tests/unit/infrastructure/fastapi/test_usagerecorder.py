from datetime import UTC, datetime, timedelta
import logging
from unittest.mock import create_autospec

import pytest

from api.domain.key.entities import Key
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import UsageRecorder, _usagerecorder
from api.infrastructure.langfuse import LangfuseRequestTracer

USER_ID = 42


@pytest.fixture
def mock_tracer():
    return create_autospec(LangfuseRequestTracer, instance=True, spec_set=True)


def _open(tracer: LangfuseRequestTracer | None) -> UsageRecorder:
    now = datetime.now(tz=UTC)

    return UsageRecorder.open(
        tracer=tracer,
        request_id="3f2a",
        endpoint="/v1/chat/completions",
        user=AuthenticatedUserView(id=USER_ID, email="alice@example.com", name="Alice", organization_id=1, permissions=[], limits=[], expires=None),
        key=Key(id=7, name="my-key", user_id=USER_ID, value="sk-...", expires=None, created=now),
    )


@pytest.fixture
def recorder(mock_tracer) -> UsageRecorder:
    return _open(mock_tracer)


def _usage(cost: float = 0.02) -> Usage:
    return Usage(prompt_tokens=7, completion_tokens=3, total_tokens=10, cost=cost, impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5))


class TestOpen:
    def test_should_build_the_record_from_the_authenticated_request(self, recorder, mock_tracer):
        # Assert
        assert recorder.record.request_id == "3f2a"
        assert recorder.record.endpoint == "/v1/chat/completions"
        assert (recorder.record.user_id, recorder.record.user_email) == (USER_ID, "alice@example.com")
        assert (recorder.record.key_id, recorder.record.key_name) == (7, "my-key")
        mock_tracer.start.assert_called_once_with(recorder.record)

    def test_should_share_its_request_id_with_the_use_case(self, recorder):
        # Assert
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

    def test_should_hand_out_a_record_that_closing_the_request_leaves_unchanged(self, recorder):
        # Arrange
        recorder.record_usage(usage=_usage(), latency=250)

        # Act
        record = recorder.get_record()
        recorder.close(status_code=500, error="RuntimeError")

        # Assert
        assert (record.status, record.error, record.usage) == (None, None, _usage())


class TestClose:
    def test_should_stamp_the_answered_status_and_end_the_trace(self, recorder, mock_tracer):
        # Arrange
        recorder.record_usage(usage=_usage(), latency=250)

        # Act
        recorder.close(status_code=200)

        # Assert
        assert (recorder.record.status, recorder.record.latency) == (200, 250)
        mock_tracer.end.assert_called_once_with(recorder.record)

    def test_should_keep_how_long_a_failed_request_took_when_the_provider_was_never_reached(self, recorder):
        # Act
        recorder.close(status_code=503, error="NoAvailableProviderError")

        # Assert
        assert recorder.record.status == 503
        assert recorder.record.error == "NoAvailableProviderError"
        assert recorder.record.latency is not None

    def test_should_keep_the_error_the_use_case_recorded_when_the_middleware_saw_none(self, recorder):
        # Arrange
        recorder.record_error(error="StatusCodeModelError")

        # Act
        recorder.close(status_code=200)

        # Assert
        assert (recorder.record.status, recorder.record.error) == (200, "StatusCodeModelError")

    def test_should_end_the_trace_once_only(self, recorder, mock_tracer):
        # Act
        recorder.close(status_code=200)
        recorder.close(status_code=500)

        # Assert
        assert recorder.record.status == 200
        mock_tracer.end.assert_called_once()

    def test_should_log_a_trace_that_fails_instead_of_failing_the_request(self, recorder, mock_tracer, monkeypatch):
        # Arrange
        mock_logger = create_autospec(logging.Logger, instance=True, spec_set=True)
        monkeypatch.setattr(_usagerecorder, "logger", mock_logger)
        mock_tracer.end.side_effect = RuntimeError("Langfuse is down")

        # Act
        recorder.close(status_code=200)

        # Assert
        mock_logger.exception.assert_called_once_with("Failed to trace the request.")

    def test_should_close_without_a_tracer_when_langfuse_is_not_configured(self):
        # Arrange
        recorder = _open(tracer=None)

        # Act
        recorder.close(status_code=200)

        # Assert
        assert recorder.is_closed
