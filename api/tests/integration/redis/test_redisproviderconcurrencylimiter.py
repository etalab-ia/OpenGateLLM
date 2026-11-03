import asyncio
from datetime import UTC, datetime
import logging
from unittest.mock import AsyncMock, create_autospec

import anyio
import pytest
from redis.exceptions import RedisError

from api.domain.provider import ProviderLimitsCannotBeEnforced, ProviderReservation, ProviderReservationRefused
from api.domain.provider.entities import Provider, ProviderLoads, ProviderType
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
    provider_concurrency_limiter = RedisProviderConcurrencyLimiter(redis_client=redis_client)
    yield provider_concurrency_limiter
    for heartbeat in provider_concurrency_limiter._heartbeats.values():
        heartbeat.cancel()


@pytest.fixture(autouse=True)
def reset_redis_outage_state(monkeypatch):
    monkeypatch.setattr(RedisProviderConcurrencyLimiter, "_redis_is_unreachable", False)
    monkeypatch.setattr(RedisProviderConcurrencyLimiter, "_requests_forwarded_without_applying_qos", 0)


@pytest.fixture
def create_provider_with_load(provider_concurrency_limiter, redis_client):
    async def create_provider_with_load(provider_id: int, qos_limit: int | None = None, ongoing_load: int = 0, expired_load: int = 0) -> Provider:
        seconds, microseconds = await redis_client.time()
        ongoing_reservation_expiry = seconds * 1000 + microseconds // 1000 + 60_000
        expired_reservation_expiry = 0
        reservations = {f"ongoing-{provider_id}-{index}": ongoing_reservation_expiry for index in range(ongoing_load)}
        reservations |= {f"expired-{provider_id}-{index}": expired_reservation_expiry for index in range(expired_load)}
        if reservations:
            await redis_client.zadd(provider_concurrency_limiter._load_key(provider_id), reservations)
        return provider(provider_id=provider_id, qos_limit=qos_limit)

    return create_provider_with_load


@pytest.fixture
def read_reservation_expiry(provider_concurrency_limiter, redis_client):
    async def read_reservation_expiry(provider: Provider, request_id: str) -> float | None:
        return await redis_client.zscore(provider_concurrency_limiter._load_key(provider.id), request_id)

    return read_reservation_expiry


@pytest.fixture
def reserve_a_provider(provider_concurrency_limiter):
    async def reserve_a_provider(request_id: str) -> ProviderReservation | ProviderReservationRefused | ProviderLimitsCannotBeEnforced:
        return await provider_concurrency_limiter.reserve(request_id=request_id, provider=provider(1), limit=None)

    return reserve_a_provider


@pytest.fixture
def wait_for_next_reservation_expiry(read_reservation_expiry):
    async def wait_for_next_reservation_expiry(provider: Provider, request_id: str, current_expiry: float) -> float:
        async def next_reservation_expiry() -> float:
            while (expiry := await read_reservation_expiry(provider, request_id=request_id)) == current_expiry:
                await asyncio.sleep(0.005)
            return expiry

        return await asyncio.wait_for(next_reservation_expiry(), timeout=1)

    return wait_for_next_reservation_expiry


class RedisOutage:
    def __init__(self, provider_concurrency_limiter: RedisProviderConcurrencyLimiter, monkeypatch: pytest.MonkeyPatch):
        self._monkeypatch = monkeypatch
        self._operations_on_a_reachable_redis = [
            (provider_concurrency_limiter, "_try_reserve", provider_concurrency_limiter._try_reserve),
            (provider_concurrency_limiter.redis_client, "time", provider_concurrency_limiter.redis_client.time),
            (provider_concurrency_limiter.redis_client, "zrem", provider_concurrency_limiter.redis_client.zrem),
        ]

    def start(self) -> None:
        for target, name, _ in self._operations_on_a_reachable_redis:
            self._monkeypatch.setattr(target, name, AsyncMock(side_effect=RedisError("unavailable")))

    def end(self) -> None:
        for target, name, operation in self._operations_on_a_reachable_redis:
            self._monkeypatch.setattr(target, name, operation)


@pytest.fixture
def redis_outage(provider_concurrency_limiter, monkeypatch):
    return RedisOutage(provider_concurrency_limiter, monkeypatch)


@pytest.mark.asyncio(loop_scope="session")
class TestReservation:
    async def test_reserve_should_hold_a_reservation_until_release_when_the_provider_has_room(self, provider_concurrency_limiter, redis_client):
        # ARRANGE
        available_provider = provider(provider_id=1)
        provider_load_key = provider_concurrency_limiter._load_key(available_provider.id)

        # ACT
        result = await provider_concurrency_limiter.reserve(request_id="request-1", provider=available_provider, limit=None)
        provider_load_while_reserved = await redis_client.zcard(provider_load_key)
        await provider_concurrency_limiter.release(reservation=result)
        provider_load_after_release = await redis_client.zcard(provider_load_key)

        # ASSERT
        assert result == ProviderReservation(provider=available_provider, request_id="request-1")
        assert provider_load_while_reserved == 1
        assert provider_load_after_release == 0

    async def test_reserve_should_refuse_a_reservation_when_the_limit_is_reached(self, provider_concurrency_limiter, create_provider_with_load):
        # ARRANGE
        full_provider = await create_provider_with_load(1, ongoing_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(request_id="request-1", provider=full_provider, limit=1)

        # ASSERT
        assert result == ProviderReservationRefused()

    async def test_reserve_should_accept_a_reservation_beyond_the_provider_limit_when_no_limit_is_given(
        self, provider_concurrency_limiter, create_provider_with_load, redis_client
    ):
        # ARRANGE
        full_provider = await create_provider_with_load(1, qos_limit=1, ongoing_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(request_id="request-1", provider=full_provider, limit=None)

        # ASSERT
        provider_load = await redis_client.zcard(provider_concurrency_limiter._load_key(full_provider.id))
        assert result == ProviderReservation(provider=full_provider, request_id="request-1")
        assert provider_load == 2

    async def test_reserve_should_ignore_expired_reservations_when_checking_the_limit(self, provider_concurrency_limiter, create_provider_with_load):
        # ARRANGE
        provider_filled_with_expired_reservations = await create_provider_with_load(1, expired_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(request_id="request-1", provider=provider_filled_with_expired_reservations, limit=1)

        # ASSERT
        assert result == ProviderReservation(provider=provider_filled_with_expired_reservations, request_id="request-1")

    async def test_reserve_should_not_exceed_the_limit_when_reservations_arrive_concurrently(self, provider_concurrency_limiter):
        # ARRANGE
        provider_with_three_reservation_slots = provider(1)

        # ACT
        attempted_reservations = await asyncio.gather(
            *[
                provider_concurrency_limiter.reserve(request_id=f"request-{index}", provider=provider_with_three_reservation_slots, limit=3)
                for index in range(10)
            ]
        )

        # ASSERT
        accepted_reservations = [reservation for reservation in attempted_reservations if isinstance(reservation, ProviderReservation)]
        assert len(accepted_reservations) == 3
        assert attempted_reservations.count(ProviderReservationRefused()) == 7

    async def test_read_loads_should_count_only_the_reservations_in_progress(self, provider_concurrency_limiter, create_provider_with_load):
        # ARRANGE
        busy_provider = await create_provider_with_load(1, ongoing_load=2, expired_load=3)
        idle_provider = await create_provider_with_load(2)

        # ACT
        result = await provider_concurrency_limiter.read_loads(providers=[busy_provider, idle_provider])

        # ASSERT
        assert result == ProviderLoads(load_by_provider_id={1: 2, 2: 0})

    async def test_release_should_free_the_reservation_even_when_called_from_a_cancelled_request(
        self, provider_concurrency_limiter, read_reservation_expiry
    ):
        # Starlette cancels the request scope when a client disconnects, so release runs where every await raises.
        # Only its first await still reaches Redis: the ZREM must be it, or the place stays taken until it expires.
        # ARRANGE
        reserved_provider = provider(1)

        # ACT
        with anyio.CancelScope() as request_scope:
            reservation = await provider_concurrency_limiter.reserve(request_id="request-1", provider=reserved_provider, limit=None)
            request_scope.cancel()
            await provider_concurrency_limiter.release(reservation=reservation)

        # ASSERT
        assert await read_reservation_expiry(reserved_provider, request_id="request-1") is None


@pytest.mark.asyncio(loop_scope="session")
class TestHeartbeat:
    async def test_heartbeat_should_extend_the_reservation_when_it_has_ticked(
        self, provider_concurrency_limiter, read_reservation_expiry, wait_for_next_reservation_expiry, redis_client
    ):
        # ARRANGE
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        reserved_provider = provider(1)
        await provider_concurrency_limiter.reserve(request_id="request-1", provider=reserved_provider, limit=None)
        expiry_at_reservation = await read_reservation_expiry(reserved_provider, request_id="request-1")

        # ACT
        expiry_after_heartbeat = await wait_for_next_reservation_expiry(
            reserved_provider, request_id="request-1", current_expiry=expiry_at_reservation
        )

        # ASSERT
        provider_load = await redis_client.zcard(provider_concurrency_limiter._load_key(reserved_provider.id))
        assert expiry_after_heartbeat > expiry_at_reservation
        assert provider_load == 1

    async def test_heartbeat_should_keep_extending_the_reservation_when_a_renewal_has_failed(
        self, provider_concurrency_limiter, read_reservation_expiry, wait_for_next_reservation_expiry, monkeypatch
    ):
        # ARRANGE
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        reserved_provider = provider(1)
        await provider_concurrency_limiter.reserve(request_id="request-1", provider=reserved_provider, limit=None)
        expiry_at_reservation = await read_reservation_expiry(reserved_provider, request_id="request-1")

        redis_time = provider_concurrency_limiter.redis_client.time
        failed_heartbeats = 0

        async def redis_time_failing_on_the_first_heartbeat():
            nonlocal failed_heartbeats
            if failed_heartbeats == 0:
                failed_heartbeats += 1
                raise RedisError("unavailable")
            return await redis_time()

        monkeypatch.setattr(provider_concurrency_limiter.redis_client, "time", redis_time_failing_on_the_first_heartbeat)

        # ACT
        expiry_after_heartbeat = await wait_for_next_reservation_expiry(
            reserved_provider, request_id="request-1", current_expiry=expiry_at_reservation
        )

        # ASSERT
        assert failed_heartbeats == 1
        assert expiry_after_heartbeat > expiry_at_reservation

    async def test_release_should_stop_the_heartbeat_of_the_reservation(self, provider_concurrency_limiter):
        # ARRANGE
        reservation = await provider_concurrency_limiter.reserve(request_id="request-1", provider=provider(1), limit=None)
        heartbeat = provider_concurrency_limiter._heartbeats["request-1"]

        # ACT
        await provider_concurrency_limiter.release(reservation=reservation)

        # ASSERT
        assert heartbeat.done()


@pytest.mark.asyncio(loop_scope="session")
class TestRedisOutage:
    async def test_reserve_should_report_that_limits_cannot_be_enforced_without_reserving_when_redis_is_unreachable(
        self, provider_concurrency_limiter, read_reservation_expiry, redis_outage
    ):
        # ARRANGE
        reserved_provider = provider(1)
        redis_outage.start()

        # ACT
        result = await provider_concurrency_limiter.reserve(request_id="request-1", provider=reserved_provider, limit=1)

        # ASSERT
        assert result == ProviderLimitsCannotBeEnforced()
        assert await read_reservation_expiry(reserved_provider, request_id="request-1") is None
        assert "request-1" not in provider_concurrency_limiter._heartbeats

    async def test_read_loads_should_report_that_limits_cannot_be_enforced_when_redis_is_unreachable(
        self, provider_concurrency_limiter, redis_outage
    ):
        # ARRANGE
        redis_outage.start()

        # ACT
        result = await provider_concurrency_limiter.read_loads(providers=[provider(1)])

        # ASSERT
        assert result == ProviderLimitsCannotBeEnforced()

    async def test_release_should_skip_redis_when_the_reservation_was_made_while_redis_was_unreachable(
        self, provider_concurrency_limiter, reserve_a_provider, redis_outage, monkeypatch
    ):
        # ARRANGE
        mock_reservation_removal = create_autospec(provider_concurrency_limiter.redis_client.zrem)
        redis_outage.start()
        await reserve_a_provider(request_id="request-1")
        reservation_made_during_the_outage = ProviderReservation(provider=provider(1), request_id="request-1")
        monkeypatch.setattr(provider_concurrency_limiter.redis_client, "zrem", mock_reservation_removal)

        # ACT
        await provider_concurrency_limiter.release(reservation=reservation_made_during_the_outage)

        # ASSERT
        mock_reservation_removal.assert_not_called()

    async def test_reserve_should_log_a_single_error_when_several_requests_hit_a_redis_outage(self, reserve_a_provider, redis_outage, caplog):
        # ARRANGE
        redis_outage.start()

        # ACT
        with caplog.at_level(logging.INFO, logger=RedisProviderConcurrencyLimiter.__module__):
            for index in range(3):
                await reserve_a_provider(request_id=f"request-{index}")

        # ASSERT
        logs = [(record.levelno, record.getMessage()) for record in caplog.records]
        assert logs == [(logging.ERROR, "Redis is unreachable: provider limits are no longer enforced.")]

    async def test_reserve_should_log_the_next_outage_from_scratch_when_redis_has_been_reachable_again(
        self, reserve_a_provider, redis_outage, caplog
    ):
        # ARRANGE
        redis_outage.start()
        await reserve_a_provider(request_id="first-outage-1")
        await reserve_a_provider(request_id="first-outage-2")
        redis_outage.end()
        await reserve_a_provider(request_id="between-outages")
        caplog.clear()

        # ACT
        with caplog.at_level(logging.INFO, logger=RedisProviderConcurrencyLimiter.__module__):
            redis_outage.start()
            await reserve_a_provider(request_id="second-outage")
            redis_outage.end()
            await reserve_a_provider(request_id="after-outages")

        # ASSERT
        logs = [(record.levelno, record.getMessage()) for record in caplog.records]
        assert logs == [
            (logging.ERROR, "Redis is unreachable: provider limits are no longer enforced."),
            (logging.INFO, "Redis is reachable again: 1 requests were forwarded without provider limits."),
        ]

    async def test_heartbeat_should_log_a_failed_renewal_at_debug_level_when_redis_is_unreachable(
        self, provider_concurrency_limiter, reserve_a_provider, redis_outage, caplog
    ):
        # ARRANGE
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        await reserve_a_provider(request_id="request-1")
        redis_outage.start()
        await reserve_a_provider(request_id="request-revealing-the-outage")
        caplog.clear()

        async def first_failed_renewal() -> logging.LogRecord:
            while not (failed_renewals := [record for record in caplog.records if record.getMessage().startswith("Failed to renew")]):
                await asyncio.sleep(0.005)
            return failed_renewals[0]

        # ACT
        with caplog.at_level(logging.DEBUG, logger=RedisProviderConcurrencyLimiter.__module__):
            failed_renewal = await asyncio.wait_for(first_failed_renewal(), timeout=1)

        # ASSERT
        assert (failed_renewal.levelno, failed_renewal.getMessage()) == (
            logging.DEBUG,
            "Failed to renew the provider reservation of request request-1.",
        )

    async def test_release_should_log_a_failed_release_at_debug_level_when_redis_is_unreachable(
        self, provider_concurrency_limiter, reserve_a_provider, redis_outage, caplog
    ):
        # ARRANGE
        reservation_made_before_the_outage = await reserve_a_provider(request_id="request-1")
        redis_outage.start()
        await reserve_a_provider(request_id="request-revealing-the-outage")
        caplog.clear()

        # ACT
        with caplog.at_level(logging.DEBUG, logger=RedisProviderConcurrencyLimiter.__module__):
            await provider_concurrency_limiter.release(reservation=reservation_made_before_the_outage)

        # ASSERT
        logs = [(record.levelno, record.getMessage()) for record in caplog.records]
        assert logs == [(logging.DEBUG, "Failed to release the provider reservation of request request-1.")]
