from datetime import UTC, datetime
import json
from unittest.mock import patch

import httpx
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest
import respx

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.langfuse import LangfuseUsageRepository

LANGFUSE_URL = "http://langfuse.test"
START_TIME = datetime(2026, 9, 1, tzinfo=UTC)
END_TIME = datetime(2026, 9, 30, tzinfo=UTC)
USAGE = Usage(
    prompt_tokens=3,
    completion_tokens=5,
    total_tokens=8,
    prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
    cost=0.01,
    impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
)
# Langfuse answers 400 on a filter column the view does not know. scores-numeric is copied from that error message,
# observations from the metrics client docstring (dimensions + high-cardinality filters).
ALLOWED_FILTER_COLUMNS = {
    "observations": {
        *("environment", "type", "name", "level", "version", "tags", "release", "traceName", "traceRelease", "traceVersion"),
        *("providedModelName", "promptName", "promptVersion", "isRootObservation", "startTimeMonth"),
        *("id", "traceId", "userId", "sessionId", "parentObservationId"),
    },
    "scores-numeric": {
        *("sessionId", "datasetRunId", "traceName", "userId", "tags", "traceRelease", "traceVersion", "observationName"),
        *("observationModelName", "observationPromptName", "observationPromptVersion", "experimentName", "experimentId"),
        *("id", "environment", "name", "evaluatorId", "ruleId", "isEvaluatorTest", "source", "dataType", "traceId"),
        *("configId", "timestampMonth", "timestampDay", "observationId", "value", "timestamp"),
    },
}


def _metrics_response(usage_rows: list[dict] | None = None, impacts_rows: list[dict] | None = None):
    def respond(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.url.params["query"])
        unknown_columns = {f["column"] for f in query["filters"]} - ALLOWED_FILTER_COLUMNS[query["view"]]
        if unknown_columns:
            return httpx.Response(400, json={"message": f"Invalid filter column {sorted(unknown_columns)}", "error": "InvalidRequestError"})
        return httpx.Response(200, json={"data": (impacts_rows if query["view"] == "scores-numeric" else usage_rows) or []})

    return respond


@pytest.fixture(scope="session")
def span_exporter():
    return InMemorySpanExporter()


@pytest.fixture(scope="session")
def langfuse_client(span_exporter):
    # The SDK caches its resources per public key: this key must stay unique to this module.
    return Langfuse(public_key="pk-lf-mocked", secret_key="sk-lf-mocked", base_url=LANGFUSE_URL, span_exporter=span_exporter)


@pytest.fixture
def mock_langfuse_api(span_exporter):
    span_exporter.clear()
    with respx.mock(base_url=LANGFUSE_URL, assert_all_called=False) as router:
        router.post("/api/public/ingestion", name="ingestion").respond(207, json={"successes": [], "errors": []})
        router.get("/api/public/v2/metrics", name="metrics").mock(side_effect=_metrics_response())
        yield router


@pytest.fixture
def repository(langfuse_client, mock_langfuse_api):
    return LangfuseUsageRepository(client=langfuse_client)


def _start_record(repository, **overrides):
    arguments = {
        "endpoint": ProviderEndpoint.CHAT_COMPLETIONS,
        "model": "chat-router",
        "user_id": 42,
        "router_id": 3,
        "router_name": "chat-router",
        "user_email": "alice@example.com",
        "key_id": 7,
        "key_name": "my-key",
    }
    return repository.start_record(**(arguments | overrides))


def _exported_spans(langfuse_client, span_exporter):
    langfuse_client.flush()
    return span_exporter.get_finished_spans()


def _ingested_scores(langfuse_client, mock_langfuse_api) -> list[dict]:
    langfuse_client.flush()
    return [event["body"] for request in mock_langfuse_api["ingestion"].calls for event in json.loads(request.request.content)["batch"]]


class TestLangfuseUsageRepositoryRecording:
    def test_exports_a_generation_with_the_request_identity(self, repository, langfuse_client, span_exporter):
        # Act
        request_id = _start_record(repository)
        repository.end_record()

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert request_id == format(span.context.trace_id, "032x")
        assert span.name == "/v1/chat/completions"
        assert span.attributes["langfuse.observation.type"] == "generation"
        assert span.attributes["langfuse.observation.model.name"] == "chat-router"
        assert span.attributes["user.id"] == "42"
        assert span.attributes["langfuse.trace.tags"] == ("key_id:7",)
        assert span.attributes["langfuse.observation.metadata.router_id"] == 3
        assert span.attributes["langfuse.observation.metadata.router_name"] == "chat-router"
        assert span.attributes["langfuse.observation.metadata.user_email"] == "alice@example.com"
        assert span.attributes["langfuse.observation.metadata.key_id"] == "7"
        assert span.attributes["langfuse.observation.metadata.key_name"] == "my-key"

    def test_exports_usage_and_impact_scores_on_update(self, repository, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        _start_record(repository)

        # Act
        repository.update_record(usage=USAGE, provider_id=9, provider_model_name="vllm-model")
        repository.end_record()

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert json.loads(span.attributes["langfuse.observation.usage_details"]) == {"input": 1, "output": 5, "input_cached_tokens": 2}
        assert json.loads(span.attributes["langfuse.observation.cost_details"]) == {"total": 0.01}
        assert span.attributes["langfuse.observation.metadata.provider_id"] == 9
        assert span.attributes["langfuse.observation.metadata.provider_model_name"] == "vllm-model"
        scores = _ingested_scores(langfuse_client, mock_langfuse_api)
        assert {(score["name"], score["value"], score["dataType"]) for score in scores} == {("kWh", 1.5, "NUMERIC"), ("kgCO2eq", 2.5, "NUMERIC")}
        assert {score["observationId"] for score in scores} == {format(span.context.span_id, "016x")}

    def test_sets_completion_start_time_when_first_token_at_is_given(self, repository, langfuse_client, span_exporter):
        # Arrange
        _start_record(repository)
        first_token_at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)

        # Act
        repository.update_record(usage=USAGE, provider_id=9, provider_model_name="vllm-model", first_token_at=first_token_at)
        repository.end_record()

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert json.loads(span.attributes["langfuse.observation.completion_start_time"]) == "2026-09-18T15:00:00Z"

    def test_marks_the_generation_as_error_on_fail(self, repository, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        _start_record(repository)

        # Act
        repository.fail_record(message="TooBusyModelError", status_code=503)
        repository.end_record()

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert span.attributes["langfuse.observation.level"] == "ERROR"
        assert span.attributes["langfuse.observation.status_message"] == "TooBusyModelError"
        assert _ingested_scores(langfuse_client, mock_langfuse_api) == []

    def test_returns_a_fallback_id_and_exports_nothing_when_start_fails(self, repository, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        with patch.object(langfuse_client, "start_observation", side_effect=RuntimeError("langfuse down")):
            # Act
            request_id = _start_record(repository)
        repository.update_record(usage=USAGE, provider_id=9, provider_model_name="vllm-model")
        repository.fail_record(message="TooBusyModelError", status_code=503)
        repository.end_record()

        # Assert
        assert len(request_id) == 32
        assert _exported_spans(langfuse_client, span_exporter) == ()
        assert _ingested_scores(langfuse_client, mock_langfuse_api) == []

    def test_swallows_end_errors(self, repository):
        # Arrange
        _start_record(repository)

        # Act / Assert
        with patch.object(repository._observation, "end", side_effect=RuntimeError("flush failed")):
            repository.end_record()
        assert repository._observation is None


def _usage_row(day: str, input_tokens=0, output_tokens=0, total_tokens=0, cost=0.0, count=0) -> dict:
    return {
        "time_dimension": day,
        "sum_inputTokens": input_tokens,
        "sum_outputTokens": output_tokens,
        "sum_totalTokens": total_tokens,
        "sum_totalCost": cost,
        "count_count": count,
    }


def _impact_row(day: str, name: str, value: float) -> dict:
    return {"name": name, "time_dimension": day, "sum_value": value}


def _filter_for(query: dict, column: str) -> dict | None:
    return next((f for f in query["filters"] if f["column"] == column), None)


@pytest.mark.asyncio(loop_scope="session")
class TestLangfuseUsageRepositoryReading:
    @staticmethod
    def _set_responses(mock_langfuse_api, usage_rows: list[dict] | None = None, impacts_rows: list[dict] | None = None) -> None:
        mock_langfuse_api["metrics"].side_effect = _metrics_response(usage_rows, impacts_rows)

    @staticmethod
    def _query_for_view(mock_langfuse_api, view: str) -> dict:
        queries = [json.loads(call.request.url.params["query"]) for call in mock_langfuse_api["metrics"].calls]
        return next(query for query in queries if query["view"] == view)

    async def test_filters_by_user_and_excludes_non_success_status(self, repository, mock_langfuse_api):
        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        query = self._query_for_view(mock_langfuse_api, "observations")
        assert query["timeDimension"] == {"granularity": "day"}
        assert _filter_for(query, "userId") == {"column": "userId", "operator": "=", "value": "6", "type": "string"}
        assert _filter_for(query, "type")["value"] == "GENERATION"
        assert _filter_for(query, "level")["value"] == "DEFAULT"

    async def test_filters_by_time_window(self, repository, mock_langfuse_api):
        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        for view in ("observations", "scores-numeric"):
            query = self._query_for_view(mock_langfuse_api, view)
            assert query["fromTimestamp"] == START_TIME.isoformat()
            assert query["toTimestamp"] == END_TIME.isoformat()

    async def test_does_not_add_optional_filters_when_absent(self, repository, mock_langfuse_api):
        # Act
        await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        for view, model_column in (("observations", "providedModelName"), ("scores-numeric", "observationModelName")):
            query = self._query_for_view(mock_langfuse_api, view)
            assert _filter_for(query, "traceName") is None
            assert _filter_for(query, "tags") is None
            assert _filter_for(query, model_column) is None

    async def test_filters_by_endpoint_model_and_key_id(self, repository, mock_langfuse_api):
        # Act
        await repository.get_usage_buckets_page(
            user_id=6,
            start_time=START_TIME,
            end_time=END_TIME,
            offset=0,
            limit=10,
            endpoint=ProviderEndpoint.CHAT_COMPLETIONS,
            model="my-router",
            key_id=7,
        )

        # Assert — the impacts query must share the usage query's context filters so both aggregate the same requests.
        for view, model_column in (("observations", "providedModelName"), ("scores-numeric", "observationModelName")):
            query = self._query_for_view(mock_langfuse_api, view)
            assert _filter_for(query, "traceName") == {"column": "traceName", "operator": "=", "value": "/v1/chat/completions", "type": "string"}
            assert _filter_for(query, "tags") == {"column": "tags", "operator": "any of", "value": ["key_id:7"], "type": "arrayOptions"}
            assert _filter_for(query, model_column) == {"column": model_column, "operator": "=", "value": "my-router", "type": "string"}

    async def test_returns_buckets_grouped_by_utc_day(self, repository, mock_langfuse_api):
        # Arrange
        self._set_responses(
            mock_langfuse_api,
            usage_rows=[_usage_row("2026-09-22", input_tokens=1800, output_tokens=892, total_tokens=2692, cost=0.5, count=7)],
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
        assert bucket.impacts == EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0)

    async def test_omits_days_with_no_usage(self, repository, mock_langfuse_api):
        # Arrange — an impact score without a usage row must not create a bucket.
        self._set_responses(
            mock_langfuse_api,
            usage_rows=[_usage_row("2026-09-22", total_tokens=10, count=1)],
            impacts_rows=[_impact_row("2026-09-22", "kWh", 1.0), _impact_row("2026-09-21", "kWh", 9.0)],
        )

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        assert page.total == 1
        assert [bucket.start_time for bucket in page.data] == [datetime(2026, 9, 22, tzinfo=UTC)]

    async def test_merges_impact_scores_into_the_matching_day(self, repository, mock_langfuse_api):
        # Arrange
        self._set_responses(
            mock_langfuse_api,
            usage_rows=[_usage_row("2026-09-22", total_tokens=10, count=2), _usage_row("2026-09-21", total_tokens=5, count=1)],
            impacts_rows=[
                _impact_row("2026-09-22", "kWh", 1.5),
                _impact_row("2026-09-22", "kgCO2eq", 0.25),
                _impact_row("2026-09-21", "kWh", 0.5),
            ],
        )

        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        impacts_query = self._query_for_view(mock_langfuse_api, "scores-numeric")
        assert impacts_query["metrics"] == [{"measure": "value", "aggregation": "sum"}]
        assert impacts_query["dimensions"] == [{"field": "name"}]
        assert _filter_for(impacts_query, "name") == {"column": "name", "operator": "any of", "value": ["kWh", "kgCO2eq"], "type": "stringOptions"}
        by_day = {bucket.start_time: bucket for bucket in page.data}
        assert by_day[datetime(2026, 9, 22, tzinfo=UTC)].impacts == EnvironmentalImpacts(kWh=1.5, kgCO2eq=0.25)
        assert by_day[datetime(2026, 9, 21, tzinfo=UTC)].impacts == EnvironmentalImpacts(kWh=0.5, kgCO2eq=0.0)

    async def test_paginates_over_days(self, repository, mock_langfuse_api):
        # Arrange
        self._set_responses(
            mock_langfuse_api,
            usage_rows=[
                _usage_row("2026-09-20", total_tokens=1, count=1),
                _usage_row("2026-09-22", total_tokens=3, count=3),
                _usage_row("2026-09-21", total_tokens=2, count=2),
            ],
        )

        # Act
        first_page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=2)
        second_page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=2, limit=2)

        # Assert
        assert first_page.total == 3
        assert [bucket.start_time.day for bucket in first_page.data] == [22, 21]
        assert second_page.total == 3
        assert [bucket.start_time.day for bucket in second_page.data] == [20]

    async def test_returns_empty_page_when_no_rows(self, repository, mock_langfuse_api):
        # Act
        page = await repository.get_usage_buckets_page(user_id=6, start_time=START_TIME, end_time=END_TIME, offset=0, limit=10)

        # Assert
        assert page.total == 0
        assert page.data == []
