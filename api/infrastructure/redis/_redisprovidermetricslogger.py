import asyncio
from collections.abc import Callable
import logging
import time

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from api.domain.provider import ProviderMetricsLogger
from api.domain.provider.entities import Metric
from api.utils.variables import METRICS__TIMESERIE_RETENTION_SECONDS, PREFIX__REDIS_METRIC_GAUGE, PREFIX__REDIS_METRIC_TIMESERIE

logger = logging.getLogger(__name__)


class RedisProviderMetricsLogger(ProviderMetricsLogger):
    PREFIX_CELERY_QUEUE_ROUTING: str = "ogl_qr"
    PREFIX_REDIS_METRIC_GAUGE: str = PREFIX__REDIS_METRIC_GAUGE
    PREFIX_REDIS_METRIC_TIMESERIE: str = PREFIX__REDIS_METRIC_TIMESERIE

    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def log_metric(self, provider_id: int, metric: Metric, value: float) -> None:
        try:
            timestamp = int(time.time() * 1000)
            # Maintain all metric series aligned per provider.
            for series_metric in (Metric.TTFT, Metric.LATENCY, Metric.NORMALIZED_LATENCY):
                series_key = f"{self.PREFIX_REDIS_METRIC_TIMESERIE}:{series_metric.value}:{provider_id}"
                await self._ensure_timeseries_exists(series_key)
                await self.redis_client.ts().add(key=series_key, timestamp=timestamp, value=value)
        except Exception:
            logger.exception(f"Failed to log request metrics ({metric.value}) in redis (id: {provider_id})")
            await self._safe_redis_reset()

    async def get_metric_history(self, provider_id: int, metric: Metric, from_time: int | None = None) -> list[float]:
        key = f"{self.PREFIX_REDIS_METRIC_TIMESERIE}:{metric.value}:{provider_id}"
        if not await self.redis_client.exists(key):
            return []

        to_time = int(time.time() * 1000)
        if from_time is None:
            from_time = to_time - METRICS__TIMESERIE_RETENTION_SECONDS * 1000
        values = await self.redis_client.ts().range(key=key, from_time=from_time, to_time=to_time)
        values = [latency for _, latency in values]

        return values

    async def increment_inflight(self, provider_id: int) -> bool:
        inflight_key = f"{self.PREFIX_REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        try:
            await self._redis_retry(self.redis_client.incr, name=inflight_key, max_retries=2)
            return True
        except Exception:
            return False

    async def decrement_inflight(self, provider_id: int, inflight_is_incremented: bool = True) -> bool:
        if not inflight_is_incremented:
            return True

        inflight_key = f"{self.PREFIX_REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        try:
            await self._redis_retry(self.redis_client.decr, name=inflight_key, max_retries=2)
            return True
        except Exception as e:
            # TODO: add a logic to reset inflight after a certain amount of time
            logger.error(msg=f"Failed to decrement inflight key {inflight_key} for provider {provider_id}: {e}")
            return False

    async def get_current_inflight(self, provider_id: int) -> int:
        key = f"{self.PREFIX_REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        if not await self.redis_client.exists(key):
            return 0

        value = await self.redis_client.get(key)
        return int(value) if value is not None else 0

    async def _ensure_timeseries_exists(self, key: str) -> None:
        try:
            await self.redis_client.ts().info(key)
        except Exception:
            try:
                await self.redis_client.ts().create(key, retention_msecs=METRICS__TIMESERIE_RETENTION_SECONDS * 1000, duplicate_policy="LAST")
            except Exception:
                pass

    async def _safe_redis_reset(self) -> None:
        """
        Safely reset a Redis client connection, catching all exceptions.

        Args:
            redis_client: The Redis client to reset
        """
        try:
            await self.redis_client.reset()
        except Exception as e:
            logger.error(msg=f"Failed to reset Redis client: {e}")

    @staticmethod
    async def _redis_retry[T](
        func: Callable[..., T],
        *args,
        max_retries: int = 3,
        backoff_base: float = 0.1,
        backoff_multiplier: float = 2.0,
        **kwargs,
    ) -> T | None:
        """
        Retry a Redis operation with exponential backoff.

        Args:
            func: The async function to retry
            *args: Arguments to pass to the function
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_base: Base delay in seconds (default: 0.1)
            backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function, or None if all retries failed

        Example:
            >>> result = await redis_retry(redis_client.incr, "my_key", max_retries=3)
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (ConnectionError, TimeoutError, RedisError) as e:
                last_exception = e

                if attempt < max_retries - 1:
                    delay = backoff_base * (backoff_multiplier**attempt)
                    logger.warning(f"Redis operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Redis operation failed after {max_retries} attempts: {last_exception}", exc_info=True)

        return None
