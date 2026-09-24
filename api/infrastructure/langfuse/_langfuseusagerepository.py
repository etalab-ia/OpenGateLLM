import asyncio
from datetime import UTC, date, datetime, timedelta
import json
import logging
from uuid import uuid4

from langfuse import Langfuse, propagate_attributes

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, Usage, UsageBucket, UsageBucketPage
from api.infrastructure.fastapi.routes import EndpointRoute

logger = logging.getLogger(__name__)

_KWH_SCORE_COLUMN = "kWh"
_KGCO2EQ_SCORE_COLUMN = "kgCO2eq"


class LangfuseUsageRepository(UsageRepository):
    def __init__(self, client: Langfuse) -> None:
        self.client = client
        self._observation = None
        self._metadata: dict = {}

    def start_record(
        self,
        endpoint: EndpointRoute,
        model: str,
        user_id: int,
        router_id: int,
        router_name: str,
        user_email: str,
        key_id: int,
        key_name: str,
    ) -> str:
        endpoint_path = f"/v1{endpoint}"
        self._metadata = {
            "endpoint": endpoint_path,
            "router_id": router_id,
            "router_name": router_name,
            "user_email": user_email,
            "key_id": str(key_id),
            "key_name": key_name,
        }
        try:
            with propagate_attributes(user_id=str(user_id)):
                self._observation = self.client.start_observation(
                    as_type="generation",
                    name=endpoint_path,
                    model=model,
                    metadata=self._metadata,
                )
            return self._observation.trace_id
        except Exception:
            logger.exception("Failed to start Langfuse observation")
            self._observation = None
            self._metadata = {}
            return uuid4().hex

    def update_record(self, usage: Usage, provider_id: int, provider_model_name: str, first_token_at: datetime | None = None) -> None:
        if self._observation is None:
            return

        try:
            self._metadata["provider_model_name"] = provider_model_name
            self._metadata["provider_id"] = provider_id
            self._metadata["status"] = 200
            update = {
                "usage_details": {
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                    "input_cached_tokens": usage.prompt_tokens_details.cached_tokens,
                },
                "cost_details": {"total": usage.cost},
                "metadata": self._metadata,
            }
            if first_token_at is not None:
                update["completion_start_time"] = first_token_at
            self._observation.update(**update)
            self._observation.score(name=_KWH_SCORE_COLUMN, value=usage.impacts.kWh, data_type="NUMERIC")
            self._observation.score(name=_KGCO2EQ_SCORE_COLUMN, value=usage.impacts.kgCO2eq, data_type="NUMERIC")
        except Exception:
            logger.exception("Failed to update Langfuse observation")

    def fail_record(self, message: str) -> None:
        if self._observation is None:
            return

        try:
            self._observation.update(level="ERROR", status_message=message)
        except Exception:
            logger.exception("Failed to mark Langfuse observation as error")

    def end_record(self) -> None:
        if self._observation is None:
            return

        try:
            self._observation.end()
        except Exception:
            logger.exception("Failed to end Langfuse observation")
        finally:
            self._observation = None
            self._metadata = {}

    async def get_usage_buckets_page(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        offset: int,
        limit: int,
        endpoint: str | None = None,
        models: list[str] | None = None,
        key_id: int | None = None,
    ) -> UsageBucketPage:
        context_filters = self._context_filters(user_id=user_id, endpoint=endpoint, models=models, key_id=key_id)
        usage_query = self._build_usage_query(context_filters, start_time=start_time, end_time=end_time)
        impacts_query = self._build_impacts_query(context_filters, start_time=start_time, end_time=end_time)

        usage_response, impacts_response = await asyncio.gather(
            asyncio.to_thread(self.client.api.metrics.metrics, query=json.dumps(usage_query)),
            asyncio.to_thread(self.client.api.metrics.metrics, query=json.dumps(impacts_query)),
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
    def _context_filters(user_id: int, endpoint: str | None, models: list[str] | None, key_id: int | None) -> list[dict]:
        """Filters shared by the usage and impacts queries so both aggregate the same requests."""
        filters: list[dict] = [{"column": "userId", "operator": "=", "value": str(user_id), "type": "string"}]
        if endpoint is not None:
            filters.append({"column": "metadata", "operator": "=", "value": endpoint, "type": "stringObject", "key": "endpoint"})
        if models:
            filters.append({"column": "providedModelName", "operator": "any of", "value": models, "type": "stringOptions"})
        if key_id is not None:
            filters.append({"column": "metadata", "operator": "=", "value": str(key_id), "type": "stringObject", "key": "key_id"})
        return filters

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
        # kWh/kgCO2eq are emitted as numeric scores in update_record (only on successful requests).
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
