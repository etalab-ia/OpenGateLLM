"""
Helper utilities for Redis operations with retry logic and error handling.
"""

import asyncio
from collections.abc import Callable
import logging

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import (
    ConnectionError,
    RedisError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


async def redis_retry[T](
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


async def safe_redis_reset(redis_client: AsyncRedis) -> None:
    """
    Safely reset a Redis client connection, catching all exceptions.

    Args:
        redis_client: The Redis client to reset
    """
    try:
        await redis_client.reset()
    except Exception as e:
        logger.debug(f"Failed to reset Redis client: {e}")
