import asyncio
from datetime import UTC, datetime
import logging
import random
from unittest.mock import AsyncMock, create_autospec

import anyio
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
        self._provider_concurrency_limiter = provider_concurrency_limiter
        self._monkeypatch = monkeypatch
        self._try_reserve_on_a_reachable_redis = provider_concurrency_limiter._try_reserve
        monkeypatch.setattr(provider_concurrency_limiter, "_try_reserve", AsyncMock(side_effect=RedisError("unavailable")))

    def end(self) -> None:
        self._monkeypatch.setattr(self._provider_concurrency_limiter, "_try_reserve", self._try_reserve_on_a_reachable_redis)


@pytest.fixture
def redis_outage(provider_concurrency_limiter, monkeypatch):
    return RedisOutage(provider_concurrency_limiter, monkeypatch)


@pytest.mark.asyncio(loop_scope="session")
class TestReservation:
    async def test_reserve_should_hold_a_reservation_until_release_when_a_provider_is_available(self, provider_concurrency_limiter, redis_client):
        # ARRANGE
        available_provider = provider(provider_id=1)
        provider_load_key = provider_concurrency_limiter._load_key(available_provider.id)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[available_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )
        provider_load_while_reserved = await redis_client.zcard(provider_load_key)
        await provider_concurrency_limiter.release(reservation=result)
        provider_load_after_release = await redis_client.zcard(provider_load_key)

        # ASSERT
        assert result == ProviderReservation(provider=available_provider, request_id="request-1")
        assert provider_load_while_reserved == 1
        assert provider_load_after_release == 0

    async def test_reserve_should_refuse_a_reservation_when_the_enforced_limit_is_reached(self, provider_concurrency_limiter):
        # ARRANGE
        provider_with_one_reservation_slot = provider(1, qos_limit=1)

        ongoing_reservation = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[provider_with_one_reservation_slot], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )

        # ACT
        attempted_reservation_on_a_full_provider = await provider_concurrency_limiter.reserve(
            request_id="request-2", providers=[provider_with_one_reservation_slot], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )

        # ASSERT
        assert attempted_reservation_on_a_full_provider == ProviderReservationRefused()

    async def test_reserve_should_accept_a_reservation_beyond_the_limit_when_the_limit_is_not_enforced(
        self, provider_concurrency_limiter, redis_client
    ):
        # ARRANGE
        available_provider = provider(1, qos_limit=1)

        ongoing_reservation = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[available_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )

        # ACT
        reservation_on_a_full_provider = await provider_concurrency_limiter.reserve(
            request_id="request-2", providers=[available_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )

        # ASSERT
        load = await redis_client.zcard(provider_concurrency_limiter._load_key(available_provider.id))
        assert ongoing_reservation.provider == available_provider
        assert reservation_on_a_full_provider.provider == available_provider
        assert load == 2

    async def test_reserve_should_refuse_a_reservation_when_the_provider_is_closed(self, provider_concurrency_limiter):
        # ARRANGE
        closed_provider = provider(1, qos_limit=0)

        # ACT
        attempted_reservation = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[closed_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )

        # ASSERT
        assert attempted_reservation == ProviderReservationRefused()

    async def test_reserve_should_fall_back_to_the_next_provider_when_one_is_full(
        self, provider_concurrency_limiter, create_provider_with_load, monkeypatch
    ):
        # ARRANGE
        full_provider = await create_provider_with_load(1, qos_limit=1, ongoing_load=1)
        free_provider = provider(2, qos_limit=1)
        mock_random_sample = create_autospec(random.sample, side_effect=lambda population, k: population)
        monkeypatch.setattr(random, "sample", mock_random_sample)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[full_provider, free_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )

        # ASSERT
        assert result.provider == free_provider

    async def test_reserve_with_least_busy_should_pick_the_lowest_load_when_a_provider_has_no_limit(
        self, provider_concurrency_limiter, create_provider_with_load
    ):
        # ARRANGE
        provider_with_limit = await create_provider_with_load(2, qos_limit=20, ongoing_load=3)
        provider_without_limit = await create_provider_with_load(1, ongoing_load=5)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1",
            providers=[provider_with_limit, provider_without_limit],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=True,
        )

        # ASSERT
        assert result.provider == provider_with_limit

    async def test_reserve_with_least_busy_should_pick_the_most_remaining_capacity_when_every_provider_has_a_limit(
        self, provider_concurrency_limiter, create_provider_with_load
    ):
        # ARRANGE
        provider_with_most_remaining_capacity = await create_provider_with_load(1, qos_limit=10, ongoing_load=5)
        least_loaded_provider = await create_provider_with_load(2, qos_limit=4, ongoing_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1",
            providers=[least_loaded_provider, provider_with_most_remaining_capacity],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=True,
        )

        # ASSERT
        assert result.provider == provider_with_most_remaining_capacity

    async def test_reserve_with_least_busy_should_pick_the_smallest_provider_id_when_loads_are_equal(self, provider_concurrency_limiter):
        # ARRANGE
        second_provider = provider(2)
        first_provider = provider(1)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[second_provider, first_provider], strategy=RouterLoadBalancingStrategy.LEAST_BUSY, enforce_limit=True
        )

        # ASSERT
        assert result.provider == first_provider

    async def test_reserve_should_ignore_expired_reservations_on_a_provider_when_sorting_providers(
        self, provider_concurrency_limiter, create_provider_with_load
    ):
        # ARRANGE
        provider_with_only_expired_reservations = await create_provider_with_load(1, expired_load=3)
        provider_with_an_ongoing_reservation = await create_provider_with_load(2, ongoing_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1",
            providers=[provider_with_an_ongoing_reservation, provider_with_only_expired_reservations],
            strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
            enforce_limit=True,
        )

        # ASSERT
        assert result.provider == provider_with_only_expired_reservations

    async def test_reserve_should_ignore_expired_reservations_on_a_provider_when_checking_its_limit(
        self, provider_concurrency_limiter, create_provider_with_load
    ):
        # ARRANGE
        provider_filled_with_expired_reservations = await create_provider_with_load(1, qos_limit=1, expired_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1",
            providers=[provider_filled_with_expired_reservations],
            strategy=RouterLoadBalancingStrategy.SHUFFLE,
            enforce_limit=True,
        )

        # ASSERT
        assert result.provider == provider_filled_with_expired_reservations

    async def test_release_should_free_the_reservation_even_when_called_from_a_cancelled_request(
        self, provider_concurrency_limiter, read_reservation_expiry
    ):
        # Starlette cancels the request scope when a client disconnects, so release runs where every await raises.
        # Only its first await still reaches Redis: the ZREM must be it, or the place stays taken until it expires.
        # ARRANGE
        reserved_provider = provider(1)

        # ACT
        with anyio.CancelScope() as request_scope:
            reservation = await provider_concurrency_limiter.reserve(
                request_id="request-1", providers=[reserved_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
            )
            request_scope.cancel()
            await provider_concurrency_limiter.release(reservation=reservation)

        # ASSERT
        assert await read_reservation_expiry(reserved_provider, request_id="request-1") is None

    async def test_reserve_should_not_exceed_the_limit_when_reservations_arrive_concurrently(self, provider_concurrency_limiter):
        # ARRANGE
        provider_with_three_reservation_slots = provider(1, qos_limit=3)

        # ACT
        attempted_reservations = await asyncio.gather(
            *[
                provider_concurrency_limiter.reserve(
                    request_id=f"request-{index}",
                    providers=[provider_with_three_reservation_slots],
                    strategy=RouterLoadBalancingStrategy.SHUFFLE,
                    enforce_limit=True,
                )
                for index in range(10)
            ]
        )

        # ASSERT
        accepted_reservations = [reservation for reservation in attempted_reservations if isinstance(reservation, ProviderReservation)]
        assert len(accepted_reservations) == 3
        assert attempted_reservations.count(ProviderReservationRefused()) == 7


@pytest.mark.asyncio(loop_scope="session")
class TestHeartbeat:
    async def test_heartbeat_should_extend_the_reservation_when_it_has_ticked(
        self, provider_concurrency_limiter, read_reservation_expiry, wait_for_next_reservation_expiry, redis_client
    ):
        # ARRANGE
        provider_concurrency_limiter.HEARTBEAT_INTERVAL_SECONDS = 0.01
        reserved_provider = provider(1)
        await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[reserved_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )
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
        await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[reserved_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )
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
        reservation = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[provider(1)], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=False
        )
        heartbeat = provider_concurrency_limiter._heartbeats["request-1"]

        # ACT
        await provider_concurrency_limiter.release(reservation=reservation)

        # ASSERT
        assert heartbeat.done()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("redis_outage")
class TestRedisOutage:
    async def test_reserve_should_accept_a_reservation_on_a_full_provider_when_redis_is_unreachable(
        self, provider_concurrency_limiter, create_provider_with_load, read_reservation_expiry
    ):
        # ARRANGE
        full_provider = await create_provider_with_load(1, qos_limit=1, ongoing_load=1)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[full_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )

        # ASSERT
        assert result == ProviderReservation(provider=full_provider, request_id="request-1")
        assert await read_reservation_expiry(full_provider, request_id="request-1") is None

    async def test_reserve_should_never_pick_a_closed_provider_when_redis_is_unreachable(self, provider_concurrency_limiter, monkeypatch):
        # ARRANGE
        closed_provider = provider(1, qos_limit=0)
        open_provider = provider(2)
        mock_random_choice = create_autospec(random.choice, side_effect=lambda candidates: candidates[0])
        monkeypatch.setattr(random, "choice", mock_random_choice)

        # ACT
        result = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[closed_provider, open_provider], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )

        # ASSERT
        mock_random_choice.assert_called_once_with([open_provider])
        assert result.provider == open_provider

    async def test_release_should_skip_redis_when_the_reservation_was_made_while_redis_was_unreachable(
        self, provider_concurrency_limiter, monkeypatch
    ):
        # ARRANGE
        reservation_made_during_the_outage = await provider_concurrency_limiter.reserve(
            request_id="request-1", providers=[provider(1)], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
        )
        mock_reservation_removal = create_autospec(provider_concurrency_limiter.redis_client.zrem)
        monkeypatch.setattr(provider_concurrency_limiter.redis_client, "zrem", mock_reservation_removal)

        # ACT
        await provider_concurrency_limiter.release(reservation=reservation_made_during_the_outage)

        # ASSERT
        mock_reservation_removal.assert_not_called()

    async def test_reserve_should_log_a_single_error_when_several_requests_hit_a_redis_outage(self, provider_concurrency_limiter, caplog):
        # ACT
        with caplog.at_level(logging.INFO, logger=RedisProviderConcurrencyLimiter.__module__):
            for index in range(3):
                await provider_concurrency_limiter.reserve(
                    request_id=f"request-{index}", providers=[provider(1)], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
                )

        # ASSERT
        logs = [(record.levelno, record.getMessage()) for record in caplog.records]
        assert logs == [(logging.ERROR, "Redis is unreachable: provider limits are no longer enforced.")]

    async def test_reserve_should_log_the_number_of_requests_forwarded_without_applying_qos_when_redis_is_reachable_again(
        self, provider_concurrency_limiter, redis_outage, caplog
    ):
        # ARRANGE
        for index in range(2):
            await provider_concurrency_limiter.reserve(
                request_id=f"request-{index}", providers=[provider(1)], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
            )
        redis_outage.end()
        caplog.clear()

        # ACT
        with caplog.at_level(logging.INFO, logger=RedisProviderConcurrencyLimiter.__module__):
            await provider_concurrency_limiter.reserve(
                request_id="request-2", providers=[provider(1)], strategy=RouterLoadBalancingStrategy.SHUFFLE, enforce_limit=True
            )

        # ASSERT
        logs = [(record.levelno, record.getMessage()) for record in caplog.records]
        assert logs == [(logging.INFO, "Redis is reachable again: 2 requests were forwarded without provider limits.")]
