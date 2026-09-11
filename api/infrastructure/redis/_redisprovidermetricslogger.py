import asyncio
from collections.abc import Callable
import logging

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from api.domain.provider import ProviderMetricsLogger
from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE

logger = logging.getLogger(__name__)


class RedisProviderMetricsLogger(ProviderMetricsLogger):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def increment_inflight(self, provider_id: int) -> bool:
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        try:
            await self._redis_retry(self.redis_client.incr, name=inflight_key, max_retries=2)
            return True
        except Exception:
            return False

    async def decrement_inflight(self, provider_id: int) -> None:
        inflight_key = f"{PREFIX__REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        try:
            await self._redis_retry(self.redis_client.decr, name=inflight_key, max_retries=2)
        except Exception as e:
            logger.error(msg=f"Failed to decrement inflight key {inflight_key} for provider {provider_id}: {e}")

    @staticmethod
    async def _redis_retry[T](
        func: Callable[..., T],
        *args,
        max_retries: int = 3,
        backoff_base: float = 0.1,
        backoff_multiplier: float = 2.0,
        **kwargs,
    ) -> T | None:
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
