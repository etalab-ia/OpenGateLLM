from datetime import UTC, datetime
from unittest.mock import MagicMock, call, create_autospec, patch

from langfuse import Langfuse
import pytest

from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.langfuse import LangfuseUsageRecorder


@pytest.fixture
def mock_client():
    return create_autospec(Langfuse, instance=True, spec_set=True)


@pytest.fixture
def mock_observation():
    observation = MagicMock()
    observation.trace_id = "b" * 32
    return observation


@pytest.fixture
def recorder(mock_client, mock_observation):
    mock_client.start_observation.return_value = mock_observation
    return LangfuseUsageRecorder(client=mock_client)


class TestLangfuseUsageRecorder:
    def test_should_return_observation_trace_id(self, recorder, mock_client, mock_observation):
        # Act
        request_id = recorder.start_record(name="chat-completions", model="chat-router", user_id=42)

        # Assert
        assert request_id == mock_observation.trace_id
        mock_client.start_observation.assert_called_once_with(as_type="generation", name="chat-completions", model="chat-router")

    def test_should_return_fallback_id_when_start_fails(self, recorder, mock_client):
        # Arrange
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")

        # Act
        request_id = recorder.start_record(name="chat-completions", model="chat-router", user_id=42)

        # Assert
        assert len(request_id) == 32

    def test_should_update_observation_with_usage(self, recorder, mock_observation):
        # Arrange
        recorder.start_record(name="chat-completions", model="chat-router", user_id=42)
        usage = Usage(
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
            prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
            cost=0.01,
            impacts=EnvironmentalImpacts(kWh=1.23456789, kgCO2eq=0.123456789),
        )

        # Act
        recorder.update_record(usage=usage, provider_id=7)

        # Assert
        mock_observation.update.assert_called_once_with(
            usage_details={"input": 3, "output": 5, "input_cached_tokens": 2},
            cost_details={"total": 0.01},
            metadata={"provider_id": 7},
        )
        mock_observation.score.assert_has_calls(
            [
                call(name="kWh", value=1.234568, data_type="NUMERIC"),
                call(name="kgCO2eq", value=0.123457, data_type="NUMERIC"),
            ]
        )

    def test_should_set_completion_start_time_when_first_token_at_is_given(self, recorder, mock_observation):
        # Arrange
        recorder.start_record(name="chat-completions", model="chat-router", user_id=42)
        first_token_at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)

        # Act
        recorder.update_record(usage=Usage(), provider_id=7, first_token_at=first_token_at)

        # Assert
        mock_observation.update.assert_called_once_with(
            usage_details={"input": 0, "output": 0, "input_cached_tokens": 0},
            cost_details={"total": 0.0},
            metadata={"provider_id": 7},
            completion_start_time=first_token_at,
        )

    def test_should_not_update_when_start_failed(self, recorder, mock_client):
        # Arrange
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")
        recorder.start_record(name="chat-completions", model="chat-router", user_id=42)

        # Act
        recorder.update_record(usage=Usage(), provider_id=1)

        # Assert
        # no observation to update — the call must not raise

    def test_should_end_observation(self, recorder, mock_observation):
        # Arrange
        recorder.start_record(name="chat-completions", model="chat-router", user_id=42)

        # Act
        recorder.end_record()

        # Assert
        mock_observation.end.assert_called_once()

    def test_should_swallow_end_errors(self, recorder, mock_observation):
        # Arrange
        recorder.start_record(name="chat-completions", model="chat-router", user_id=42)
        mock_observation.end.side_effect = RuntimeError("flush failed")

        # Act / Assert
        recorder.end_record()

    def test_should_propagate_user_id_when_starting(self, recorder):
        # Arrange
        with patch("api.infrastructure.langfuse._langfuseusagerecord.propagate_attributes") as mock_propagate:
            mock_propagate.return_value.__enter__.return_value = None
            mock_propagate.return_value.__exit__.return_value = None

            # Act
            recorder.start_record(name="chat-completions", model="chat-router", user_id=42)

        # Assert
        mock_propagate.assert_called_once_with(user_id="42")
