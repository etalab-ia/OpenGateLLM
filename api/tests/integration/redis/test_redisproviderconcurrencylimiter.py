import asyncio
from datetime import UTC, datetime

import pytest
from redis.exceptions import RedisError

from api.domain.provider import ProviderReservation, ProviderReservationRefused
from api.domain.provider.entities import Provider, ProviderType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.infrastructure.redis import RedisProviderConcurrencyLimiter


def provider(provider_id: int, qos_limit: int | None = None) -> Provider:
    return Provider(
        id=provider_id,
        router_id=1,
        user_id=1,
        type=ProviderType.VLLM,
        url="http://test",
        timeout=30,
        model_name=f"test-model-{provider_id}",
        qos_limit=qos_limit,
        created=datetime.now(tz=UTC),
        updated=datetime.now(tz=UTC),
    )


@pytest.fixture
def provider_concurrency_limiter(redis_client):
    return RedisProviderConcurrencyLimiter(redis_client=redis_client)


async def set_load(
    provider_concurrency_limiter: RedisProviderConcurrencyLimiter, redis_client, provider_id: int, load: int, score: int | None = None
) -> None:
    if score is None:
        seconds, microseconds = await redis_client.time()
        score = seconds * 1000 + microseconds // 1000 + 60_000
    await redis_client.zadd(
        provider_concurrency_limiter._load_key(provider_id),
        {f"existing-{provider_id}-{index}": score for index in range(load)},
    )


async def reserve(
    limiter: RedisProviderConcurrencyLimiter,
    request_id: str,
    providers: list[Provider],
    strategy=RouterLoadBalancingStrategy.SHUFFLE,
    enforce_limit=True,
):
    return await limiter.reserve(request_id=request_id, providers=providers, strategy=strategy, enforce_limit=enforce_limit)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderConcurrencyLimiter:
    async def test_reserves_tracks_and_releases_request(self, provider_concurrency_limiter, redis_client):
        candidate = provider(1)
        key = provider_concurrency_limiter._load_key(candidate.id)

        result = await reserve(provider_concurrency_limiter, "request-1", [candidate], enforce_limit=False)
        load_while_reserved = await redis_client.zcard(key)
        await provider_concurrency_limiter.release(reservation=result)

        assert result == ProviderReservation(provider=candidate, request_id="request-1")
        assert load_while_reserved == 1
        assert await redis_client.zcard(key) == 0

    async def test_refuses_atomically_when_enforced_limit_is_full(self, provider_concurrency_limiter):
        candidate = provider(1, qos_limit=1)

        first = await reserve(provider_concurrency_limiter, "request-1", [candidate])
        second = await reserve(provider_concurrency_limiter, "request-2", [candidate])
        await provider_concurrency_limiter.release(reservation=first)

        assert second == ProviderReservationRefused()

    async def test_over_reserves_when_limit_is_not_enforced(self, provider_concurrency_limiter, redis_client):
        candidate = provider(1, qos_limit=1)

        first = await reserve(provider_concurrency_limiter, "request-1", [candidate], enforce_limit=False)
        second = await reserve(provider_concurrency_limiter, "request-2", [candidate], enforce_limit=False)
        load = await redis_client.zcard(provider_concurrency_limiter._load_key(candidate.id))
        await provider_concurrency_limiter.release(reservation=first)
        await provider_concurrency_limiter.release(reservation=second)

        assert first.provider == candidate
        assert second.provider == candidate
        assert load == 2

    async def test_never_reserves_on_closed_provider(self, provider_concurrency_limiter):
        candidate = provider(1, qos_limit=0)

        result = await reserve(provider_concurrency_limiter, "request-1", [candidate], enforce_limit=False)

        assert result == ProviderReservationRefused()

    async def test_falls_back_to_the_next_provider_when_one_is_full(self, provider_concurrency_limiter, redis_client):
        full = provider(1, qos_limit=1)
        free = provider(2, qos_limit=1)
        await set_load(provider_concurrency_limiter, redis_client, full.id, 1)

        # shuffle tries the full provider first about half of the time
        chosen_providers = []
        for index in range(5):
            result = await reserve(provider_concurrency_limiter, f"request-{index}", [full, free])
            await provider_concurrency_limiter.release(reservation=result)
            chosen_providers.append(result.provider)

        assert chosen_providers == [free] * 5

    async def test_least_busy_uses_raw_load_when_any_provider_is_uncapped(self, provider_concurrency_limiter, redis_client):
        capped = provider(2, qos_limit=20)
        uncapped = provider(1)
        await set_load(provider_concurrency_limiter, redis_client, capped.id, 3)
        await set_load(provider_concurrency_limiter, redis_client, uncapped.id, 1)

        result = await reserve(provider_concurrency_limiter, "request-1", [capped, uncapped], strategy=RouterLoadBalancingStrategy.LEAST_BUSY)
        await provider_concurrency_limiter.release(reservation=result)

        assert result.provider == uncapped

    async def test_least_busy_uses_remaining_capacity_when_all_providers_are_capped(self, provider_concurrency_limiter, redis_client):
        high_load_high_capacity = provider(1, qos_limit=10)
        low_load_low_capacity = provider(2, qos_limit=4)
        await set_load(provider_concurrency_limiter, redis_client, high_load_high_capacity.id, 8)
        await set_load(provider_concurrency_limiter, redis_client, low_load_low_capacity.id, 1)

        result = await reserve(
            provider_concurrency_limiter,
            "request-1",
            [high_load_high_capacity, low_load_low_capacity],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
        )
        await provider_concurrency_limiter.release(reservation=result)

        assert result.provider == low_load_low_capacity

    async def test_least_busy_breaks_ties_with_smallest_provider_id(self, provider_concurrency_limiter):
        larger_id = provider(2)
        smaller_id = provider(1)

        result = await reserve(provider_concurrency_limiter, "request-1", [larger_id, smaller_id], strategy=RouterLoadBalancingStrategy.LEAST_BUSY)
        await provider_concurrency_limiter.release(reservation=result)

        assert result.provider == smaller_id

    async def test_least_busy_ignores_expired_reservations(self, provider_concurrency_limiter, redis_client):
        expired_only = provider(1)
        busy = provider(2)
        await set_load(provider_concurrency_limiter, redis_client, expired_only.id, 3, score=0)
        await set_load(provider_concurrency_limiter, redis_client, busy.id, 1)

        result = await reserve(provider_concurrency_limiter, "request-1", [busy, expired_only], strategy=RouterLoadBalancingStrategy.LEAST_BUSY)
        await provider_concurrency_limiter.release(reservation=result)

        assert result.provider == expired_only

    async def test_expired_reservations_do_not_count_against_the_limit(self, provider_concurrency_limiter, redis_client):
        candidate = provider(1, qos_limit=1)
        await set_load(provider_concurrency_limiter, redis_client, candidate.id, 1, score=0)

        result = await reserve(provider_concurrency_limiter, "request-1", [candidate])
        await provider_concurrency_limiter.release(reservation=result)

        assert result.provider == candidate

    async def test_heartbeat_refreshes_expiry_without_changing_load(self, provider_concurrency_limiter, redis_client):
        candidate = provider(1)
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        provider_concurrency_limiter.RESERVATION_TTL_MILLISECONDS = 1_000
        key = provider_concurrency_limiter._load_key(candidate.id)

        reservation = await reserve(provider_concurrency_limiter, "request-1", [candidate], enforce_limit=False)
        initial_score = await redis_client.zscore(key, "request-1")
        await asyncio.sleep(0.03)
        refreshed_score = await redis_client.zscore(key, "request-1")
        load = await redis_client.zcard(key)
        await provider_concurrency_limiter.release(reservation=reservation)

        assert refreshed_score > initial_score
        assert load == 1

    async def test_heartbeat_keeps_renewing_after_a_redis_failure(self, provider_concurrency_limiter, redis_client, monkeypatch):
        candidate = provider(1)
        key = provider_concurrency_limiter._load_key(candidate.id)
        await redis_client.zadd(key, {"request-1": 0})
        real_time = redis_client.time
        calls = 0

        async def time_failing_once():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RedisError("unavailable")
            return await real_time()

        monkeypatch.setattr(provider_concurrency_limiter.redis_client, "time", time_failing_once)
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01

        heartbeat = asyncio.create_task(provider_concurrency_limiter._heartbeat(key=key, request_id="request-1"))
        await asyncio.sleep(0.05)
        heartbeat.cancel()

        assert calls >= 2
        assert await redis_client.zscore(key, "request-1") > 0

    async def test_release_stops_the_heartbeat(self, provider_concurrency_limiter, redis_client):
        candidate = provider(1)
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        key = provider_concurrency_limiter._load_key(candidate.id)

        reservation = await reserve(provider_concurrency_limiter, "request-1", [candidate], enforce_limit=False)
        await provider_concurrency_limiter.release(reservation=reservation)
        await asyncio.sleep(0.03)

        assert await redis_client.zscore(key, "request-1") is None

    async def test_concurrent_reservations_do_not_exceed_capacity(self, provider_concurrency_limiter):
        candidate = provider(1, qos_limit=3)

        results = await asyncio.gather(*[reserve(provider_concurrency_limiter, f"request-{index}", [candidate]) for index in range(10)])
        reservations = [result for result in results if isinstance(result, ProviderReservation)]
        for reservation in reservations:
            await provider_concurrency_limiter.release(reservation=reservation)

        assert len(reservations) == 3
        assert sum(isinstance(result, ProviderReservationRefused) for result in results) == 7
