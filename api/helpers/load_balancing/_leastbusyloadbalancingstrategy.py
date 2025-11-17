from datetime import datetime, timedelta
import logging
import math
import random

from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from api.helpers.load_balancing import BaseLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.utils.variables import PREFIX__REDIS_METRIC_TIMESERIE, REDIS__TIMESERIE_RETENTION_SECONDS

logger = logging.getLogger(__name__)


class LeastBusyLoadBalancingStrategy(BaseLoadBalancingStrategy):
    def __init__(self, redis_client: AsyncRedis | Redis, load_balancing_metric: Metric = Metric.TTFT) -> None:
        """
        Get a provider to handle the request based on the specified routing strategy.

        Args:
            candidates (list[int]): The list of provider candidates (provider IDs) to choose from
            redis_client (AsyncRedis): Redis client instance, required for least busy strategy
            load_balancing_metric (Metric): The type of metric to use for performance evaluation

        Returns:
            tuple[int, float | None]: A tuple containing:
                - provider_id (int): The chosen provider ID
                - performance_indicator (float | None): Performance metric for the chosen provider, if applicable
        """
        self.metric = load_balancing_metric
        self.redis_client = redis_client
        self.percentile = 0.95

    def apply_sync_strategy(self, candidates: list[int]) -> tuple[int, float]:
        scores = {}
        for provider_id in candidates:
            cutoff = datetime.now() - timedelta(seconds=REDIS__TIMESERIE_RETENTION_SECONDS)
            key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{self.metric}:{provider_id}"  # currently only TTFT is supported
            try:
                result = self.redis_client.ts().range(key, from_time=int(cutoff.timestamp() * 1000) if cutoff else 0, to_time="+")
                series = [(ts, val) for ts, val in result]

            except Exception as e:
                logger.error(f"Failed to fetch timeseries for {key}: {e}", exc_info=True)
                self.redis_client.reset()
                series = []

            if not series:
                scores[provider_id] = float("inf")
                continue

            values = [v for _, v in series]
            values.sort()

            idx = math.ceil(self.percentile * len(values)) - 1
            scores[provider_id] = values[idx]

        min_value = min(scores.values())
        candidates = [k for k, v in scores.items() if v == min_value]

        return random.choice(candidates), min_value

    async def apply_async_strategy(self, candidates: list[int]) -> tuple[int, float]:
        scores = {}
        for provider_id in candidates:
            cutoff = datetime.now() - timedelta(seconds=REDIS__TIMESERIE_RETENTION_SECONDS)
            key = f"{PREFIX__REDIS_METRIC_TIMESERIE}:{self.metric}:{provider_id}"  # currently only TTFT is supported
            try:
                result = await self.redis_client.ts().range(key, from_time=int(cutoff.timestamp() * 1000) if cutoff else 0, to_time="+")
                series = [(ts, val) for ts, val in result]

            except Exception as e:
                logger.error(f"Failed to fetch timeseries for {key}: {e}", exc_info=True)
                await self.redis_client.reset()
                series = []

            if not series:
                scores[provider_id] = float("inf")
                continue

            values = [v for _, v in series]
            values.sort()

            idx = math.ceil(self.percentile * len(values)) - 1
            scores[provider_id] = values[idx]

        min_value = min(scores.values())
        candidates = [k for k, v in scores.items() if v == min_value]

        return random.choice(candidates), min_value
