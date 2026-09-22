from datetime import UTC, datetime
from unittest.mock import MagicMock, call, create_autospec, patch

from langfuse import Langfuse
import pytest

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.langfuse import LangfuseUsageRecorder

IDENTITY_METADATA = {
    "router_id": 3,
    "router_name": "chat-router",
    "user_email": "alice@example.com",
    "key_id": 7,
    "key_name": "my-key",
}


def _start_record(recorder, **overrides):
    return recorder.start_record(
        endpoint=ProviderEndpoint.CHAT_COMPLETIONS,
        model="chat-router",
        user_id=42,
        **IDENTITY_METADATA,
        **overrides,
    )


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
        request_id = _start_record(recorder)

        # Assert
        assert request_id == mock_observation.trace_id
        mock_client.start_observation.assert_called_once_with(
            as_type="generation",
            name="chat-completions",
            model="chat-router",
            metadata=IDENTITY_METADATA,
        )

    def test_should_return_fallback_id_when_start_fails(self, recorder, mock_client):
        # Arrange
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")

        # Act
        request_id = _start_record(recorder)

        # Assert
        assert len(request_id) == 32

    def test_should_update_observation_with_usage(self, recorder, mock_observation):
        # Arrange
        _start_record(recorder)
        usage = Usage(
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
            prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
            cost=0.01,
            impacts=EnvironmentalImpacts(kWh=1.23456789, kgCO2eq=0.123456789),
        )

        # Act
        recorder.update_record(usage=usage, provider_id=7, provider_model_name="vllm-model")

        # Assert
        mock_observation.update.assert_called_once_with(
            usage_details={"input": 3, "output": 5, "input_cached_tokens": 2},
            cost_details={"total": 0.01},
            metadata={**IDENTITY_METADATA, "provider_model_name": "vllm-model", "provider_id": 7},
        )
        mock_observation.score.assert_has_calls(
            [
                call(name="kWh", value=1.234568, data_type="NUMERIC"),
                call(name="kgCO2eq", value=0.123457, data_type="NUMERIC"),
            ]
        )

    def test_should_set_completion_start_time_when_first_token_at_is_given(self, recorder, mock_observation):
        # Arrange
        _start_record(recorder)
        first_token_at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)

        # Act
        recorder.update_record(usage=Usage(), provider_id=7, provider_model_name="vllm-model", first_token_at=first_token_at)

        # Assert
        mock_observation.update.assert_called_once_with(
            usage_details={"input": 0, "output": 0, "input_cached_tokens": 0},
            cost_details={"total": 0.0},
            metadata={**IDENTITY_METADATA, "provider_model_name": "vllm-model", "provider_id": 7},
            completion_start_time=first_token_at,
        )

    def test_should_not_update_when_start_failed(self, recorder, mock_client):
        # Arrange
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")
        _start_record(recorder)

        # Act
        recorder.update_record(usage=Usage(), provider_id=1, provider_model_name="vllm-model")

        # Assert
        # no observation to update — the call must not raise

    def test_should_mark_observation_as_error_with_status_message(self, recorder, mock_observation):
        # Arrange
        _start_record(recorder)

        # Act
        recorder.fail_record(message="TooBusyModelError")

        # Assert
        mock_observation.update.assert_called_once_with(level="ERROR", status_message="TooBusyModelError")

    def test_should_not_fail_when_start_failed(self, recorder, mock_client):
        # Arrange
        mock_client.start_observation.side_effect = RuntimeError("langfuse down")
        _start_record(recorder)

        # Act / Assert
        recorder.fail_record(message="TooBusyModelError")

    def test_should_end_observation(self, recorder, mock_observation):
        # Arrange
        _start_record(recorder)

        # Act
        recorder.end_record()

        # Assert
        mock_observation.end.assert_called_once()

    def test_should_swallow_end_errors(self, recorder, mock_observation):
        # Arrange
        _start_record(recorder)
        mock_observation.end.side_effect = RuntimeError("flush failed")

        # Act / Assert
        recorder.end_record()

    def test_should_propagate_user_id_when_starting(self, recorder):
        # Arrange
        with patch("api.infrastructure.langfuse._langfuseusagerecord.propagate_attributes") as mock_propagate:
            mock_propagate.return_value.__enter__.return_value = None
            mock_propagate.return_value.__exit__.return_value = None

            # Act
            _start_record(recorder)

        # Assert
        mock_propagate.assert_called_once_with(user_id="42")
