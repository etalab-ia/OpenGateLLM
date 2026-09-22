import asyncio
from datetime import UTC, datetime, timedelta
import json
import logging
from uuid import uuid4

from langfuse import Langfuse, propagate_attributes

from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts, Usage, UsageBucket, UsageBucketPage
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


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
        self._metadata = {
            "endpoint": f"/v1{endpoint}",
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
                    name=endpoint.strip("/").replace("/", "-"),
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
            self._observation.score(name="kWh", value=usage.impacts.kWh, data_type="NUMERIC")
            self._observation.score(name="kgCO2eq", value=usage.impacts.kgCO2eq, data_type="NUMERIC")
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
        query = self._build_metrics_query(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            endpoint=endpoint,
            models=models,
            key_id=key_id,
        )
        response = await asyncio.to_thread(self.client.api.metrics.metrics, query=json.dumps(query))
        rows = list(getattr(response, "data", None) or [])

        buckets = sorted((self._row_to_usage_bucket(row) for row in rows), key=lambda bucket: bucket.start_time, reverse=True)
        return UsageBucketPage(total=len(buckets), data=buckets[offset : offset + limit])

    @staticmethod
    def _build_metrics_query(
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        endpoint: str | None,
        models: list[str] | None,
        key_id: int | None,
    ) -> dict:
        filters: list[dict] = [
            {"column": "userId", "operator": "=", "value": str(user_id), "type": "string"},
            {"column": "type", "operator": "=", "value": "GENERATION", "type": "string"},
            {"column": "level", "operator": "=", "value": "DEFAULT", "type": "string"},
        ]
        if endpoint is not None:
            filters.append({"column": "metadata", "operator": "=", "value": endpoint, "type": "stringObject", "key": "endpoint"})
        if models:
            filters.append({"column": "providedModelName", "operator": "any of", "value": models, "type": "stringOptions"})
        if key_id is not None:
            filters.append({"column": "metadata", "operator": "=", "value": str(key_id), "type": "stringObject", "key": "key_id"})

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

    @staticmethod
    def _row_to_usage_bucket(row: dict) -> UsageBucket:
        start_time = datetime.fromisoformat(str(row["time_dimension"])).replace(tzinfo=UTC)
        return UsageBucket(
            start_time=start_time,
            end_time=start_time + timedelta(days=1),
            prompt_tokens=int(row.get("sum_inputTokens") or 0),
            completion_tokens=int(row.get("sum_outputTokens") or 0),
            total_tokens=int(row.get("sum_totalTokens") or 0),
            cost=float(row.get("sum_totalCost") or 0.0),
            requests=int(row.get("count_count") or 0),
            # TODO kWh/kgCO2eq are stored as Langfuse scores, which the Metrics V2 observations view canno't agg
            impacts=EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0),
        )
