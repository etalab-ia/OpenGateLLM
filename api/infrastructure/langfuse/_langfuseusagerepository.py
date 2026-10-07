import asyncio
from datetime import UTC, date, datetime, timedelta
import json
import logging

from langfuse import Langfuse, propagate_attributes

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, UsageBucket, UsageBucketPage, UsageRecord

logger = logging.getLogger(__name__)

_KWH_SCORE_COLUMN = "kWh"
_KGCO2EQ_SCORE_COLUMN = "kgCO2eq"


class LangfuseUsageRepository(UsageRepository):
    def __init__(self, client: Langfuse) -> None:
        self.client = client
        self._observation = None

    def open_record(self, record: UsageRecord) -> None:
        """The observation is an OpenTelemetry span: it has to be open while the provider is called, so it starts here
        and is filled in by save_record. The router is not resolved yet, hence no model until then."""
        try:
            with propagate_attributes(user_id=str(record.user_id), tags=[self._key_tag(record.key_id)]):
                self._observation = self.client.start_observation(
                    # the id the API answers in X-Request-ID, so a client can point at its own trace
                    trace_context={"trace_id": record.request_id},
                    as_type="generation",
                    name=record.endpoint,
                    metadata=self._metadata(record),
                )
        except Exception:
            logger.exception("Failed to start Langfuse observation")
            self._observation = None

    async def save_record(self, record: UsageRecord) -> None:
        if self._observation is None:
            logger.warning("Cannot end Langfuse observation: no active observation (start_observation likely failed)")
            return

        try:
            self._observation.update(**self._build_update(record))
            if (usage := record.usage) is not None:
                self._observation.score(name=_KWH_SCORE_COLUMN, value=usage.impacts.kWh, data_type="NUMERIC")
                self._observation.score(name=_KGCO2EQ_SCORE_COLUMN, value=usage.impacts.kgCO2eq, data_type="NUMERIC")
            self._observation.end()
        finally:
            self._observation = None

    def _build_update(self, record: UsageRecord) -> dict:
        update: dict = {"model": record.router_name, "metadata": self._metadata(record)}

        if record.status is None or record.status // 100 != 2:
            # get_usage_buckets_page filters on level == DEFAULT, so a failed request must not count as consumption
            update["level"] = "ERROR"
            update["status_message"] = record.error
        if record.ttft is not None:
            update["completion_start_time"] = record.created + timedelta(milliseconds=record.ttft)
        if (usage := record.usage) is not None:
            update["usage_details"] = {
                # Langfuse sums every "input*" key into inputTokens, so "input" must exclude the cached tokens.
                "input": usage.prompt_tokens - usage.prompt_tokens_details.cached_tokens,
                "output": usage.completion_tokens,
                "input_cached_tokens": usage.prompt_tokens_details.cached_tokens,
            }
            update["cost_details"] = {"total": usage.cost}

        return update

    @staticmethod
    def _metadata(record: UsageRecord) -> dict:
        return {
            "router_id": record.router_id,
            "router_name": record.router_name,
            "user_email": record.user_email,
            "key_id": str(record.key_id),
            "key_name": record.key_name,
            "provider_id": record.provider_id,
            "provider_model_name": record.provider_model_name,
            "status": record.status,
            "latency": record.latency,
        }

    async def get_usage_buckets_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
        model: str | None = None,
        key_id: int | None = None,
    ) -> UsageBucketPage:
        context_filters = self._context_filters(user_id=user_id, endpoint=endpoint, key_id=key_id)
        usage_filters = [*context_filters, *self._model_filter("providedModelName", model)]
        impacts_filters = [*context_filters, *self._model_filter("observationModelName", model)]
        usage_query = self._build_usage_query(usage_filters, start_time=start_time, end_time=end_time)
        impacts_query = self._build_impacts_query(impacts_filters, start_time=start_time, end_time=end_time)

        usage_response, impacts_response = await asyncio.gather(
            self.client.async_api.metrics.metrics(query=json.dumps(usage_query)),
            self.client.async_api.metrics.metrics(query=json.dumps(impacts_query)),
        )
        impacts_by_day = self._impacts_by_day(list(getattr(impacts_response, "data", None) or []))
        usage_rows = list(getattr(usage_response, "data", None) or [])

        buckets = sorted(
            (self._row_to_usage_bucket(row, impacts_by_day) for row in usage_rows),
            key=lambda bucket: bucket.start_time,
            reverse=True,
        )
        return UsageBucketPage(total=len(buckets), data=buckets[offset : offset + limit])

    @staticmethod
    def _key_tag(key_id: int) -> str:
        return f"key_id:{key_id}"

    @classmethod
    def _context_filters(cls, user_id: int, endpoint: str | None, key_id: int | None) -> list[dict]:
        """Filters valid on both the observations and scores-numeric views, so both queries aggregate the same requests.

        The scores views cannot filter on metadata, so the key is matched through the trace tag set in open_record.
        """
        filters: list[dict] = [{"column": "userId", "operator": "=", "value": str(user_id), "type": "string"}]
        if endpoint is not None:
            filters.append({"column": "traceName", "operator": "=", "value": endpoint, "type": "string"})
        if key_id is not None:
            filters.append({"column": "tags", "operator": "any of", "value": [cls._key_tag(key_id)], "type": "arrayOptions"})
        return filters

    @staticmethod
    def _model_filter(column: str, model: str | None) -> list[dict]:
        """The model column is named differently on each view: providedModelName vs observationModelName."""
        if model is None:
            return []
        return [{"column": column, "operator": "=", "value": model, "type": "string"}]

    @classmethod
    def _build_usage_query(cls, context_filters: list[dict], start_time: datetime, end_time: datetime) -> dict:
        filters = [
            *context_filters,
            {"column": "type", "operator": "=", "value": "GENERATION", "type": "string"},
            {"column": "level", "operator": "=", "value": "DEFAULT", "type": "string"},
        ]
        return {
            "view": "observations",
            "metrics": [
                {"measure": "inputTokens", "aggregation": "sum"},
                {"measure": "outputTokens", "aggregation": "sum"},
                {"measure": "totalTokens", "aggregation": "sum"},
                {"measure": "totalCost", "aggregation": "sum"},
                {"measure": "count", "aggregation": "count"},
            ],
            "dimensions": [],
            "filters": filters,
            "timeDimension": {"granularity": "day"},
            "fromTimestamp": start_time.astimezone(UTC).isoformat(),
            "toTimestamp": end_time.astimezone(UTC).isoformat(),
            "orderBy": [{"field": "time_dimension", "direction": "desc"}],
            "config": {"row_limit": 1000},
        }

    @classmethod
    def _build_impacts_query(cls, context_filters: list[dict], start_time: datetime, end_time: datetime) -> dict:
        # kWh/kgCO2eq are emitted as numeric scores in save_record, and only when the provider answered.
        filters = [
            *context_filters,
            {"column": "name", "operator": "any of", "value": [_KWH_SCORE_COLUMN, _KGCO2EQ_SCORE_COLUMN], "type": "stringOptions"},
        ]
        return {
            "view": "scores-numeric",
            "metrics": [{"measure": "value", "aggregation": "sum"}],
            "dimensions": [{"field": "name"}],
            "filters": filters,
            "timeDimension": {"granularity": "day"},
            "fromTimestamp": start_time.astimezone(UTC).isoformat(),
            "toTimestamp": end_time.astimezone(UTC).isoformat(),
            "orderBy": [{"field": "time_dimension", "direction": "desc"}],
            "config": {"row_limit": 1000},
        }

    @classmethod
    def _impacts_by_day(cls, rows: list[dict]) -> dict[date, dict[str, float]]:
        impacts: dict[date, dict[str, float]] = {}
        for row in rows:
            name = row.get("name")
            if name not in (_KWH_SCORE_COLUMN, _KGCO2EQ_SCORE_COLUMN):
                continue
            day = cls._parse_day(row["time_dimension"])
            impacts.setdefault(day, {_KWH_SCORE_COLUMN: 0.0, _KGCO2EQ_SCORE_COLUMN: 0.0})[name] += float(row.get("sum_value") or 0.0)
        return impacts

    @classmethod
    def _row_to_usage_bucket(cls, row: dict, impacts_by_day: dict[date, dict[str, float]]) -> UsageBucket:
        day = cls._parse_day(row["time_dimension"])
        start_time = datetime(day.year, day.month, day.day, tzinfo=UTC)
        impacts = impacts_by_day.get(day, {})
        return UsageBucket(
            start_time=start_time,
            end_time=start_time + timedelta(days=1),
            prompt_tokens=int(row.get("sum_inputTokens") or 0),
            completion_tokens=int(row.get("sum_outputTokens") or 0),
            total_tokens=int(row.get("sum_totalTokens") or 0),
            cost=float(row.get("sum_totalCost") or 0.0),
            requests=int(row.get("count_count") or 0),
            impacts=EnvironmentalImpacts(kWh=impacts.get(_KWH_SCORE_COLUMN, 0.0), kgCO2eq=impacts.get(_KGCO2EQ_SCORE_COLUMN, 0.0)),
        )

    @staticmethod
    def _parse_day(value: object) -> date:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
