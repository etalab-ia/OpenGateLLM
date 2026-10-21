from datetime import UTC, datetime, timedelta
import json
from unittest.mock import patch

from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest
import respx

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage, UsageRecord
from api.infrastructure.langfuse import LangfuseRequestTracer

LANGFUSE_URL = "http://langfuse.test"
REQUEST_ID = "a1b2" * 8
CREATED = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
USAGE = Usage(
    prompt_tokens=3,
    completion_tokens=5,
    total_tokens=8,
    prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
    cost=0.01,
    impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
)


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
        yield router


@pytest.fixture
def tracer(langfuse_client, mock_langfuse_api):
    return LangfuseRequestTracer(client=langfuse_client)


def _record(**overrides) -> UsageRecord:
    fields = {
        "request_id": REQUEST_ID,
        "endpoint": f"/v1{ProviderEndpoint.CHAT_COMPLETIONS}",
        "created": CREATED,
        "user_id": 42,
        "user_email": "alice@example.com",
        "key_id": 7,
        "key_name": "my-key",
        "router_id": 3,
        "router_name": "chat-router",
        "provider_id": 9,
        "provider_model_name": "vllm-model",
        "usage": USAGE,
        "status": 200,
        "latency": 250,
    }
    return UsageRecord(**(fields | overrides))


def _exported_spans(langfuse_client, span_exporter):
    langfuse_client.flush()
    return span_exporter.get_finished_spans()


def _ingested_scores(langfuse_client, mock_langfuse_api) -> list[dict]:
    langfuse_client.flush()
    return [event["body"] for request in mock_langfuse_api["ingestion"].calls for event in json.loads(request.request.content)["batch"]]


@pytest.mark.asyncio(loop_scope="function")
class TestLangfuseRequestTracer:
    async def test_exports_a_generation_with_the_request_identity(self, tracer, langfuse_client, span_exporter):
        # Arrange
        record = _record()

        # Act
        tracer.start(record)
        tracer.end(record)

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert format(span.context.trace_id, "032x") == REQUEST_ID, "the trace is addressable by the id the API answered"
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
        assert span.attributes["langfuse.observation.metadata.status"] == 200
        assert span.attributes["langfuse.observation.metadata.latency"] == 250

    async def test_exports_usage_and_impact_scores(self, tracer, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        record = _record()

        # Act
        tracer.start(record)
        tracer.end(record)

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert json.loads(span.attributes["langfuse.observation.usage_details"]) == {"input": 1, "output": 5, "input_cached_tokens": 2}
        assert json.loads(span.attributes["langfuse.observation.cost_details"]) == {"total": 0.01}
        assert span.attributes["langfuse.observation.metadata.provider_id"] == 9
        assert span.attributes["langfuse.observation.metadata.provider_model_name"] == "vllm-model"
        scores = _ingested_scores(langfuse_client, mock_langfuse_api)
        assert {(score["name"], score["value"], score["dataType"]) for score in scores} == {("kWh", 1.5, "NUMERIC"), ("kgCO2eq", 2.5, "NUMERIC")}
        assert {score["observationId"] for score in scores} == {format(span.context.span_id, "016x")}

    async def test_sets_the_completion_start_time_from_the_recorded_ttft(self, tracer, langfuse_client, span_exporter):
        # Arrange
        record = _record(ttft=50)

        # Act
        tracer.start(record)
        tracer.end(record)

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        exported = json.loads(span.attributes["langfuse.observation.completion_start_time"])
        assert datetime.fromisoformat(exported.replace("Z", "+00:00")) == CREATED + timedelta(milliseconds=50)

    async def test_marks_the_generation_as_error_when_the_api_answered_a_failure(self, tracer, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        record = _record(status=503, error="TooBusyModelError", usage=None, provider_id=None, provider_model_name=None)

        # Act
        tracer.start(record)
        tracer.end(record)

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert span.attributes["langfuse.observation.level"] == "ERROR"
        assert span.attributes["langfuse.observation.status_message"] == "TooBusyModelError"
        assert _ingested_scores(langfuse_client, mock_langfuse_api) == []

    async def test_marks_the_generation_as_error_when_a_stream_failed_after_answering_200(self, tracer, langfuse_client, span_exporter):
        # Arrange
        record = _record(status=200, error="StatusCodeModelError")

        # Act
        tracer.start(record)
        tracer.end(record)

        # Assert
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert span.attributes["langfuse.observation.level"] == "ERROR"
        assert span.attributes["langfuse.observation.status_message"] == "StatusCodeModelError"

    async def test_still_exports_the_generation_when_updating_it_fails(self, tracer, langfuse_client, span_exporter):
        # Arrange
        record = _record()
        tracer.start(record)

        # Act / Assert
        with patch.object(tracer._observation, "update", side_effect=RuntimeError("invalid usage_details")):
            with pytest.raises(RuntimeError):
                tracer.end(record)
        [span] = _exported_spans(langfuse_client, span_exporter)
        assert format(span.context.trace_id, "032x") == REQUEST_ID

    async def test_exports_nothing_when_opening_the_observation_fails(self, tracer, langfuse_client, span_exporter, mock_langfuse_api):
        # Arrange
        record = _record()

        # Act
        with patch.object(langfuse_client, "start_observation", side_effect=RuntimeError("langfuse down")):
            tracer.start(record)
        tracer.end(record)

        # Assert
        assert _exported_spans(langfuse_client, span_exporter) == ()
        assert _ingested_scores(langfuse_client, mock_langfuse_api) == []

    async def test_releases_the_observation_when_ending_it_fails(self, tracer):
        # Arrange
        record = _record()
        tracer.start(record)

        # Act / Assert
        with patch.object(tracer._observation, "end", side_effect=RuntimeError("flush failed")):
            with pytest.raises(RuntimeError):
                tracer.end(record)
        assert tracer._observation is None
