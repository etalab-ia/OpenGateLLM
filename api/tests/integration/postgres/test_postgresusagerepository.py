from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.domain import EntitiesPage
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage, UsageBucket, UsageRecord
from api.infrastructure.postgres import PostgresUsageRepository
from api.infrastructure.postgres.models import Usage as UsageTable
from api.tests.integration.conftest import CurrentDbSessionFactory
from api.tests.integration.factories.sql import KeySQLFactory, ProviderSQLFactory, UsageSQLFactory, UserSQLFactory

CHAT_COMPLETIONS = "/v1/chat/completions"
EMBEDDINGS = "/v1/embeddings"
DAY = datetime(2026, 8, 1, tzinfo=UTC)
NEXT_DAY = datetime(2026, 8, 2, tzinfo=UTC)
THIRD_DAY = datetime(2026, 8, 3, tzinfo=UTC)
CREATED = datetime(2026, 9, 21, 10, 0, tzinfo=UTC)


def _usage() -> Usage:
    return Usage(
        prompt_tokens=3,
        completion_tokens=5,
        total_tokens=8,
        prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
        cost=0.01,
        impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
    )


@pytest.fixture
def repository(db_session):
    return PostgresUsageRepository(postgres_session=db_session, session_factory=CurrentDbSessionFactory())


async def _seed(db_session):
    provider = ProviderSQLFactory()
    key = KeySQLFactory(user=provider.router.user)
    await db_session.flush()
    return key, provider


def _record(key, provider, **overrides) -> UsageRecord:
    fields = {
        "request_id": "3f2a",
        "endpoint": CHAT_COMPLETIONS,
        "created": CREATED,
        "user_id": key.user.id,
        "user_email": key.user.email,
        "key_id": key.id,
        "key_name": key.name,
        "router_id": provider.router.id,
        "router_name": provider.router.name,
        "provider_id": provider.id,
        "provider_model_name": provider.model_name,
        "usage": _usage(),
        "status": 200,
        "latency": 250,
    }
    return UsageRecord(**(fields | overrides))


async def _persisted_rows(db_session) -> list[UsageTable]:
    return list((await db_session.scalars(select(UsageTable))).all())


def _window():
    return DAY, THIRD_DAY + timedelta(days=1)


@pytest.mark.asyncio(loop_scope="session")
class TestSaveRecord:
    async def test_persists_every_field_of_the_record(self, repository, db_session):
        # Arrange
        key, provider = await _seed(db_session)

        # Act
        await repository.save_record(_record(key, provider, ttft=50))

        # Assert
        [row] = await _persisted_rows(db_session)
        assert row.request_id == "3f2a"
        assert row.endpoint == CHAT_COMPLETIONS
        assert row.created == CREATED
        assert row.user_id == key.user.id
        assert row.user_email == key.user.email
        assert row.token_id == key.id
        assert row.token_name == key.name
        assert row.router_id == provider.router.id
        assert row.router_name == provider.router.name
        assert row.provider_id == provider.id
        assert row.provider_model_name == provider.model_name
        assert row.prompt_tokens == 3
        assert row.completion_tokens == 5
        assert row.total_tokens == 8
        assert row.cost == 0.01
        assert row.kwh == 1.5
        assert row.kgco2eq == 2.5
        assert row.status == 200
        assert row.latency == 250
        assert row.ttft == 50
        assert row.created.tzinfo is not None

    @pytest.mark.parametrize("status", [503, 429, None], ids=["provider-failure", "rate-limited", "no-response"])
    async def test_persists_nothing_for_a_request_that_did_not_succeed(self, repository, db_session, status):
        # Arrange
        key, provider = await _seed(db_session)
        record = _record(key, provider, provider_id=None, provider_model_name=None, usage=None, status=status, error="NoAvailableProviderError")

        # Act
        await repository.save_record(record)

        # Assert
        assert await _persisted_rows(db_session) == []

    async def test_persists_a_stream_that_answered_200_then_broke(self, repository, db_session):
        # Arrange: the status is fixed by the first chunk, and the tokens already delivered must be counted
        key, provider = await _seed(db_session)
        record = _record(key, provider, status=200, error="ProviderNotReachableError")

        # Act
        await repository.save_record(record)

        # Assert
        [row] = await _persisted_rows(db_session)
        assert (row.status, row.completion_tokens) == (200, 5)

    async def test_persists_nothing_when_the_record_is_only_opened(self, repository, db_session):
        # Arrange: Postgres has nothing to write until the record is complete
        key, provider = await _seed(db_session)

        # Act
        repository.open_record(_record(key, provider))

        # Assert
        assert await _persisted_rows(db_session) == []

    async def test_raises_when_the_row_breaks_a_foreign_key(self, repository, db_session):
        # Arrange: the caller logs it — the adapter must not swallow an unknown integrity failure
        key, provider = await _seed(db_session)

        # Act / Assert
        with pytest.raises(IntegrityError):
            await repository.save_record(_record(key, provider, user_id=key.user.id + 1_000_000))


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsageBucketsPage:
    async def test_returns_buckets_grouped_by_utc_day(self, repository, db_session):
        user = UserSQLFactory()
        other_user = UserSQLFactory()
        UsageSQLFactory(
            user=user,
            router_name="own-model",
            created=DAY.replace(hour=10),
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost=0.1,
            kwh=0.01,
            kgco2eq=0.02,
        )
        UsageSQLFactory(
            user=user,
            router_name="own-model",
            created=DAY.replace(hour=22),
            prompt_tokens=5,
            completion_tokens=5,
            total_tokens=10,
            cost=0.05,
            kwh=0.005,
            kgco2eq=0.01,
        )
        UsageSQLFactory(
            user=user,
            router_name="own-model",
            created=NEXT_DAY.replace(hour=1),
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost=0.01,
            kwh=0.001,
            kgco2eq=0.002,
        )
        UsageSQLFactory(user=other_user, router_name="other-model", created=DAY.replace(hour=12))
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert isinstance(result, EntitiesPage)
        assert result.total == 2
        assert len(result.data) == 2
        newest, oldest = result.data
        assert isinstance(newest, UsageBucket)
        assert newest.start_time == NEXT_DAY
        assert newest.end_time == THIRD_DAY
        assert newest.prompt_tokens == 1
        assert newest.completion_tokens == 1
        assert newest.total_tokens == 2
        assert newest.cost == pytest.approx(0.01)
        assert newest.requests == 1
        assert newest.impacts == EnvironmentalImpacts(kWh=0.001, kgCO2eq=0.002)

        assert oldest.start_time == DAY
        assert oldest.end_time == NEXT_DAY
        assert oldest.prompt_tokens == 15
        assert oldest.completion_tokens == 25
        assert oldest.total_tokens == 40
        assert oldest.cost == pytest.approx(0.15)
        assert oldest.requests == 2
        assert oldest.impacts == EnvironmentalImpacts(kWh=0.015, kgCO2eq=0.03)

    async def test_omits_days_with_no_usage(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12))
        UsageSQLFactory(user=user, created=THIRD_DAY.replace(hour=12))
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.total == 2
        assert [bucket.start_time for bucket in result.data] == [THIRD_DAY, DAY]

    async def test_excludes_non_success_status(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), status=200, prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=DAY.replace(hour=13), failed=True, prompt_tokens=99, total_tokens=99)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.total == 1
        assert result.data[0].prompt_tokens == 10

    async def test_filters_by_endpoint(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), endpoint=CHAT_COMPLETIONS, prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=DAY.replace(hour=13), embeddings=True, prompt_tokens=3, total_tokens=3)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=10,
            endpoint=EMBEDDINGS,
        )

        assert result.total == 1
        assert result.data[0].prompt_tokens == 3

    async def test_filters_by_model(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), router_name="model-a", prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=DAY.replace(hour=13), router_name="model-b", prompt_tokens=4, total_tokens=4)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=10,
            model="model-a",
        )

        assert result.total == 1
        assert result.data[0].prompt_tokens == 10

    async def test_filters_by_key_id(self, repository, db_session):
        user = UserSQLFactory()
        matching_key = KeySQLFactory(user=user, name="matching-key")
        other_key = KeySQLFactory(user=user, name="other-key")
        await db_session.flush()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), token_id=matching_key.id, prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=DAY.replace(hour=13), token_id=other_key.id, prompt_tokens=4, total_tokens=4)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=10,
            key_id=matching_key.id,
        )

        assert result.total == 1
        assert result.data[0].prompt_tokens == 10

    async def test_filters_by_time_window(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=THIRD_DAY.replace(hour=12), prompt_tokens=4, total_tokens=4)
        await db_session.flush()

        result = await repository.get_usage_buckets_page(
            user_id=user.id,
            start_time=DAY,
            end_time=NEXT_DAY,
            offset=0,
            limit=10,
        )

        assert result.total == 1
        assert result.data[0].start_time == DAY

    async def test_maps_null_environmental_impacts_to_zero(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), kwh=None, kgco2eq=None)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.data[0].impacts == EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0)

    async def test_paginates_over_days(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12))
        UsageSQLFactory(user=user, created=NEXT_DAY.replace(hour=12))
        UsageSQLFactory(user=user, created=THIRD_DAY.replace(hour=12))
        await db_session.flush()

        start_time, end_time = _window()
        first_page = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=2)
        second_page = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=2, limit=2)

        assert first_page.total == 3
        assert [bucket.start_time for bucket in first_page.data] == [THIRD_DAY, NEXT_DAY]
        assert second_page.total == 3
        assert [bucket.start_time for bucket in second_page.data] == [DAY]

    async def test_returns_empty_page_when_no_rows(self, repository, db_session):
        user = UserSQLFactory()
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.total == 0
        assert result.data == []
