import asyncio
from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis as AsyncRedis

from api.domain.provider._providerqosadmission import QosAdmissionFull, QosAdmissionGranted
from api.domain.provider.entities import Provider, ProviderType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.infrastructure.redis._redisproviderqosadmission import RedisProviderQosAdmission
from api.utils.variables import PREFIX__REDIS_QOS_LOAD, QOS_HEARTBEAT_TTL_MS


def _provider(provider_id: int, qos_limit: float | None = None) -> Provider:
    return Provider(
        id=provider_id,
        router_id=1,
        user_id=1,
        type=ProviderType.VLLM,
        url="http://test",
        timeout=30,
        model_name="test-model",
        qos_limit=qos_limit,
        created=datetime.now(tz=UTC),
        updated=datetime.now(tz=UTC),
    )


@pytest.fixture
def admission(redis_client: AsyncRedis) -> RedisProviderQosAdmission:
    return RedisProviderQosAdmission(redis_client=redis_client)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisProviderQosAdmission:
    async def test_try_admit_admits_and_reserves_slot(self, admission: RedisProviderQosAdmission, redis_client: AsyncRedis):
        # Arrange
        providers = [_provider(1, qos_limit=2), _provider(2, qos_limit=2)]

        # Act
        result = await admission.try_admit(
            providers=providers,
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            request_id="req-1",
        )

        # Assert
        assert isinstance(result, QosAdmissionGranted)
        key = f"{PREFIX__REDIS_QOS_LOAD}:{result.provider_id}"
        members = await redis_client.zrange(key, 0, -1)
        assert [member.decode() if isinstance(member, bytes) else member for member in members] == ["req-1"]

    async def test_try_admit_returns_full_when_all_providers_are_at_capacity(self, admission: RedisProviderQosAdmission, redis_client: AsyncRedis):
        # Arrange
        provider = _provider(10, qos_limit=1)
        key = f"{PREFIX__REDIS_QOS_LOAD}:{provider.id}"
        now_ms = int(asyncio.get_running_loop().time() * 1000)  # not wall clock; use time.time
        import time

        await redis_client.zadd(key, {"existing": int(time.time() * 1000) + QOS_HEARTBEAT_TTL_MS})

        # Act
        result = await admission.try_admit(
            providers=[provider],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            request_id="req-2",
        )

        # Assert
        assert result == QosAdmissionFull(depth=1)

    async def test_try_admit_least_busy_picks_provider_with_most_remaining_capacity(
        self, admission: RedisProviderQosAdmission, redis_client: AsyncRedis
    ):
        # Arrange
        tight = _provider(20, qos_limit=2)
        roomy = _provider(21, qos_limit=5)
        import time

        now = int(time.time() * 1000) + QOS_HEARTBEAT_TTL_MS
        await redis_client.zadd(f"{PREFIX__REDIS_QOS_LOAD}:{tight.id}", {"a": now})
        await redis_client.zadd(f"{PREFIX__REDIS_QOS_LOAD}:{roomy.id}", {"b": now})

        # Act
        result = await admission.try_admit(
            providers=[tight, roomy],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            request_id="req-3",
        )

        # Assert
        assert result == QosAdmissionGranted(provider_id=roomy.id)

    async def test_release_removes_member(self, admission: RedisProviderQosAdmission, redis_client: AsyncRedis):
        # Arrange
        provider = _provider(30, qos_limit=None)
        await admission.try_admit(
            providers=[provider],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            request_id="req-4",
        )
        await admission.start_heartbeat(provider_id=provider.id, request_id="req-4")

        # Act
        await admission.release(provider_id=provider.id, request_id="req-4")

        # Assert
        assert await redis_client.zcard(f"{PREFIX__REDIS_QOS_LOAD}:{provider.id}") == 0

    async def test_try_admit_purges_expired_members_before_counting(self, admission: RedisProviderQosAdmission, redis_client: AsyncRedis):
        # Arrange
        provider = _provider(40, qos_limit=1)
        key = f"{PREFIX__REDIS_QOS_LOAD}:{provider.id}"
        await redis_client.zadd(key, {"zombie": 1})  # already expired

        # Act
        result = await admission.try_admit(
            providers=[provider],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            request_id="req-5",
        )

        # Assert
        assert result == QosAdmissionGranted(provider_id=provider.id)
        members = await redis_client.zrange(key, 0, -1)
        assert [member.decode() if isinstance(member, bytes) else member for member in members] == ["req-5"]
