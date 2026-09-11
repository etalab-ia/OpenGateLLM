import asyncio
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from api.domain.provider import ProviderAdmissionFull
from api.domain.provider.entities import Provider, ProviderType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.infrastructure.redis import RedisProviderQoS


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
def provider_qos(redis_client):
    return RedisProviderQoS(redis_client=redis_client)


async def set_load(provider_qos: RedisProviderQoS, redis_client, provider_id: int, load: int, score: int | None = None) -> None:
    if score is None:
        seconds, microseconds = await redis_client.time()
        score = seconds * 1000 + microseconds // 1000 + 60_000
    await redis_client.zadd(
        provider_qos._load_key(provider_id),
        {f"existing-{provider_id}-{index}": score for index in range(load)},
    )


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderQoS:
    async def test_admits_tracks_and_releases_request(self, provider_qos, redis_client):
        candidate = provider(1)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[candidate],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            enforce_limit=False,
        ) as result:
            assert result == candidate
            assert await redis_client.zcard(provider_qos._load_key(candidate.id)) == 1

        assert await redis_client.zcard(provider_qos._load_key(candidate.id)) == 0

    async def test_rejects_atomically_when_enforced_limit_is_full(self, provider_qos):
        candidate = provider(1, qos_limit=1)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[candidate],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            enforce_limit=True,
        ):
            async with provider_qos.admit(
                request_id="request-2",
                providers=[candidate],
                strategy=RouterLoadBalancingStrategy.SHUFFLE,
                enforce_limit=True,
            ) as result:
                assert result == ProviderAdmissionFull(depth=1)

    async def test_over_admits_when_limit_is_not_enforced(self, provider_qos):
        candidate = provider(1, qos_limit=1)

        async with AsyncExitStack() as stack:
            first = await stack.enter_async_context(
                provider_qos.admit(
                    request_id="request-1",
                    providers=[candidate],
                    strategy=RouterLoadBalancingStrategy.SHUFFLE,
                    enforce_limit=False,
                )
            )
            second = await stack.enter_async_context(
                provider_qos.admit(
                    request_id="request-2",
                    providers=[candidate],
                    strategy=RouterLoadBalancingStrategy.SHUFFLE,
                    enforce_limit=False,
                )
            )

            assert first == candidate
            assert second == candidate
            assert await provider_qos.get_loads([candidate.id]) == {candidate.id: 2}

    async def test_never_admits_closed_provider(self, provider_qos):
        candidate = provider(1, qos_limit=0)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[candidate],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            enforce_limit=False,
        ) as result:
            assert result == ProviderAdmissionFull(depth=0)

    async def test_least_busy_uses_raw_load_when_any_provider_is_uncapped(self, provider_qos, redis_client):
        capped = provider(2, qos_limit=20)
        uncapped = provider(1)
        await set_load(provider_qos, redis_client, capped.id, 3)
        await set_load(provider_qos, redis_client, uncapped.id, 1)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[capped, uncapped],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=False,
        ) as result:
            assert result == uncapped

    async def test_least_busy_uses_remaining_capacity_when_all_providers_are_capped(self, provider_qos, redis_client):
        high_load_high_capacity = provider(1, qos_limit=10)
        low_load_low_capacity = provider(2, qos_limit=4)
        await set_load(provider_qos, redis_client, high_load_high_capacity.id, 8)
        await set_load(provider_qos, redis_client, low_load_low_capacity.id, 1)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[high_load_high_capacity, low_load_low_capacity],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=True,
        ) as result:
            assert result == low_load_low_capacity

    async def test_least_busy_breaks_ties_with_smallest_provider_id(self, provider_qos):
        larger_id = provider(2)
        smaller_id = provider(1)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[larger_id, smaller_id],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=False,
        ) as result:
            assert result == smaller_id

    async def test_purges_expired_members_from_every_provider_before_selecting(self, provider_qos, redis_client):
        first = provider(1)
        second = provider(2)
        await set_load(provider_qos, redis_client, first.id, 1, score=0)
        await set_load(provider_qos, redis_client, second.id, 1, score=0)

        async with provider_qos.admit(
            request_id="request-1",
            providers=[first, second],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=False,
        ):
            assert await redis_client.zcard(provider_qos._load_key(second.id)) == 0

    async def test_heartbeat_refreshes_expiry_without_changing_load(self, provider_qos, redis_client):
        candidate = provider(1)
        provider_qos.HEARTBEAT_INTERVAL_SECONDS = 0.01
        provider_qos.HEARTBEAT_TTL_MILLISECONDS = 1_000

        async with provider_qos.admit(
            request_id="request-1",
            providers=[candidate],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            enforce_limit=False,
        ):
            key = provider_qos._load_key(candidate.id)
            initial_score = await redis_client.zscore(key, "request-1")
            await asyncio.sleep(0.03)
            refreshed_score = await redis_client.zscore(key, "request-1")

            assert refreshed_score > initial_score
            assert await redis_client.zcard(key) == 1

    async def test_heartbeat_removes_member_after_three_redis_failures(self, provider_qos, redis_client, monkeypatch):
        candidate = provider(1)
        key = provider_qos._load_key(candidate.id)
        await set_load(provider_qos, redis_client, candidate.id, 1)
        await redis_client.zadd(key, {"request-1": (await redis_client.time())[0] * 1000 + 60_000})
        mock_time = AsyncMock(side_effect=RedisError("unavailable"))
        monkeypatch.setattr(provider_qos.redis_client, "time", mock_time)
        provider_qos.HEARTBEAT_INTERVAL_SECONDS = 0
        provider_qos.HEARTBEAT_RETRY_BASE_SECONDS = 0

        await provider_qos._heartbeat(provider_id=candidate.id, request_id="request-1")

        assert mock_time.await_count == 3
        assert await redis_client.zscore(key, "request-1") is None

    async def test_concurrent_admissions_do_not_exceed_capacity(self, provider_qos):
        candidate = provider(1, qos_limit=3)
        entered = asyncio.Event()
        release = asyncio.Event()
        results = []

        async def admit(index: int) -> None:
            async with provider_qos.admit(
                request_id=f"request-{index}",
                providers=[candidate],
                strategy=RouterLoadBalancingStrategy.SHUFFLE,
                enforce_limit=True,
            ) as result:
                results.append(result)
                if len(results) == 10:
                    entered.set()
                if isinstance(result, Provider):
                    await release.wait()

        tasks = [asyncio.create_task(admit(index)) for index in range(10)]
        await entered.wait()
        assert sum(isinstance(result, Provider) for result in results) == 3
        assert sum(isinstance(result, ProviderAdmissionFull) for result in results) == 7
        release.set()
        await asyncio.gather(*tasks)
