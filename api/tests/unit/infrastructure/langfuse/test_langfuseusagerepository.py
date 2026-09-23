from datetime import UTC, datetime
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, call, create_autospec, patch

from langfuse import Langfuse
import pytest

from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.langfuse import LangfuseUsageRepository
from api.utils.variables import EndpointRoute

IDENTITY_METADATA = {
    "router_id": 3,
    "router_name": "chat-router",
    "user_email": "alice@example.com",
    "key_id": 7,
    "key_name": "my-key",
}

EXPECTED_START_METADATA = {"endpoint": "/v1/chat/completions", **IDENTITY_METADATA, "key_id": "7"}


def _start_record(recorder, **overrides):
    return recorder.start_record(
        endpoint=EndpointRoute.CHAT_COMPLETIONS,
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
    return LangfuseUsageRepository(client=mock_client)


class TestLangfuseUsageRepositoryRecording:
    def test_should_return_observation_trace_id(self, recorder, mock_client, mock_observation):
        # Act
        request_id = _start_record(recorder)

        # Assert
        assert request_id == mock_observation.trace_id
        mock_client.start_observation.assert_called_once_with(
            as_type="generation",
            name="/v1/chat/completions",
            model="chat-router",
            metadata=EXPECTED_START_METADATA,
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
            metadata={**EXPECTED_START_METADATA, "provider_model_name": "vllm-model", "provider_id": 7, "status": 200},
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
            metadata={**EXPECTED_START_METADATA, "provider_model_name": "vllm-model", "provider_id": 7, "status": 200},
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
        with patch("api.infrastructure.langfuse._langfuseusagerepository.propagate_attributes") as mock_propagate:
            mock_propagate.return_value.__enter__.return_value = None
            mock_propagate.return_value.__exit__.return_value = None

            # Act
            _start_record(recorder)

        # Assert
        mock_propagate.assert_called_once_with(user_id="42")


START_TIME = datetime(2026, 9, 1, tzinfo=UTC)
END_TIME = datetime(2026, 9, 30, tzinfo=UTC)


def _metrics_row(day: str, *, input_tokens=0, output_tokens=0, total_tokens=0, cost=0.0, count=0) -> dict:
    return {
        "time_dimension": day,
        "sum_inputTokens": input_tokens,
        "sum_outputTokens": output_tokens,
        "sum_totalTokens": total_tokens,
        "sum_totalCost": cost,
        "count_count": count,
    }


def _filter_for(query: dict, column: str) -> dict | None:
    return next((f for f in query["filters"] if f["column"] == column), None)


def _metadata_filter_for(query: dict, key: str) -> dict | None:
    return next((f for f in query["filters"] if f["column"] == "metadata" and f.get("key") == key), None)


class TestLangfuseUsageRepositoryReading:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def repository(self, mock_client):
        return LangfuseUsageRepository(client=mock_client)

    def _set_responses(self, mock_client, *, usage_rows: list[dict] | None = None, impacts_rows: list[dict] | None = None) -> None:
        usage_rows = usage_rows or []
        impacts_rows = impacts_rows or []

        def _dispatch(*, query: str):
            view = json.loads(query)["view"]
            rows = impacts_rows if view == "scores-numeric" else usage_rows
            return SimpleNamespace(data=rows)

        mock_client.api.metrics.metrics.side_effect = _dispatch

    def _query_for_view(self, mock_client, view: str) -> dict:
        for call_args in mock_client.api.metrics.metrics.call_args_list:
            query = json.loads(call_args.kwargs["query"])
            if query["view"] == view:
                return query
        raise AssertionError(f"no metrics query issued for view {view!r}")

    async def test_should_filter_usage_query_on_user_success_and_time_range(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client)

        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        query = self._query_for_view(mock_client, "observations")
        assert query["timeDimension"] == {"granularity": "day"}
        assert query["fromTimestamp"] == START_TIME.isoformat()
        assert query["toTimestamp"] == END_TIME.isoformat()
        assert _filter_for(query, "userId") == {"column": "userId", "operator": "=", "value": "6", "type": "string"}
        assert _filter_for(query, "type")["value"] == "GENERATION"
        assert _filter_for(query, "level")["value"] == "DEFAULT"

    async def test_should_query_numeric_impact_scores_over_the_same_range(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client)

        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        query = self._query_for_view(mock_client, "scores-numeric")
        assert query["metrics"] == [{"measure": "value", "aggregation": "sum"}]
        assert query["dimensions"] == [{"field": "name"}]
        assert query["timeDimension"] == {"granularity": "day"}
        assert query["fromTimestamp"] == START_TIME.isoformat()
        assert _filter_for(query, "userId") == {"column": "userId", "operator": "=", "value": "6", "type": "string"}
        assert _filter_for(query, "name") == {"column": "name", "operator": "any of", "value": ["kWh", "kgCO2eq"], "type": "stringOptions"}

    async def test_should_not_add_optional_filters_when_absent(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client)

        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        query = self._query_for_view(mock_client, "observations")
        assert _metadata_filter_for(query, "endpoint") is None
        assert _metadata_filter_for(query, "key_id") is None
        assert _filter_for(query, "providedModelName") is None

    async def test_should_add_endpoint_model_and_key_filters_to_both_queries(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client)

        # Act
        await repository.get_usage_buckets_page(
            user_id=6,
            start_time=START_TIME,
            end_time=END_TIME,
            offset=0,
            limit=10,
            endpoint="/v1/chat/completions",
            models=["my-router", "other-router"],
            key_id=7,
        )

        # Assert — the impacts query must share the usage query's context filters so both aggregate the same requests.
        for view in ("observations", "scores-numeric"):
            query = self._query_for_view(mock_client, view)
            assert _metadata_filter_for(query, "endpoint") == {
                "column": "metadata",
                "operator": "=",
                "value": "/v1/chat/completions",
                "type": "stringObject",
                "key": "endpoint",
            }
            assert _metadata_filter_for(query, "key_id") == {
                "column": "metadata",
                "operator": "=",
                "value": "7",
                "type": "stringObject",
                "key": "key_id",
            }
            assert _filter_for(query, "providedModelName") == {
                "column": "providedModelName",
                "operator": "any of",
                "value": ["my-router", "other-router"],
                "type": "stringOptions",
            }

    async def test_should_map_rows_to_daily_buckets(self, repository, mock_client):
        # Arrange
        self._set_responses(
            mock_client, usage_rows=[_metrics_row("2026-09-22", input_tokens=1800, output_tokens=892, total_tokens=2692, cost=0.5, count=7)]
        )

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        assert page.total == 1
        bucket = page.data[0]
        assert bucket.start_time == datetime(2026, 9, 22, tzinfo=UTC)
        assert bucket.end_time == datetime(2026, 9, 23, tzinfo=UTC)
        assert bucket.prompt_tokens == 1800
        assert bucket.completion_tokens == 892
        assert bucket.total_tokens == 2692
        assert bucket.cost == 0.5
        assert bucket.requests == 7

    async def test_should_merge_impact_scores_into_the_matching_day(self, repository, mock_client):
        # Arrange
        self._set_responses(
            mock_client,
            usage_rows=[
                _metrics_row("2026-09-22", total_tokens=10, count=2),
                _metrics_row("2026-09-21", total_tokens=5, count=1),
            ],
            impacts_rows=[
                {"time_dimension": "2026-09-22", "name": "kWh", "sum_value": 1.5},
                {"time_dimension": "2026-09-22", "name": "kgCO2eq", "sum_value": 0.25},
                {"time_dimension": "2026-09-21", "name": "kWh", "sum_value": 0.5},
            ],
        )

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        by_day = {bucket.start_time: bucket for bucket in page.data}
        assert by_day[datetime(2026, 9, 22, tzinfo=UTC)].impacts.kWh == 1.5
        assert by_day[datetime(2026, 9, 22, tzinfo=UTC)].impacts.kgCO2eq == 0.25
        assert by_day[datetime(2026, 9, 21, tzinfo=UTC)].impacts.kWh == 0.5
        # No kgCO2eq score for the 21st -> defaults to 0.
        assert by_day[datetime(2026, 9, 21, tzinfo=UTC)].impacts.kgCO2eq == 0.0

    async def test_should_default_impacts_to_zero_when_no_scores_returned(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client, usage_rows=[_metrics_row("2026-09-22", total_tokens=10, count=2)], impacts_rows=[])

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        assert page.data[0].impacts.kWh == 0.0
        assert page.data[0].impacts.kgCO2eq == 0.0

    async def test_should_sort_buckets_by_day_descending_and_page_client_side(self, repository, mock_client):
        # Arrange
        self._set_responses(
            mock_client,
            usage_rows=[
                _metrics_row("2026-09-20", total_tokens=1, count=1),
                _metrics_row("2026-09-22", total_tokens=3, count=3),
                _metrics_row("2026-09-21", total_tokens=2, count=2),
            ],
        )

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=1, limit=1)

        # Assert
        assert page.total == 3
        assert len(page.data) == 1
        assert page.data[0].start_time == datetime(2026, 9, 21, tzinfo=UTC)

    async def test_should_return_empty_page_when_no_rows(self, repository, mock_client):
        # Arrange
        self._set_responses(mock_client)

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        assert page.total == 0
        assert page.data == []

    async def test_should_propagate_metrics_api_errors(self, repository, mock_client):
        # Arrange
        mock_client.api.metrics.metrics.side_effect = RuntimeError("langfuse metrics 500")

        # Act / Assert
        with pytest.raises(RuntimeError, match="langfuse metrics 500"):
            await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)
