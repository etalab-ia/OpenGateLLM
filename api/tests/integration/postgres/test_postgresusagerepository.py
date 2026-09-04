from datetime import UTC, datetime, timedelta

import pytest

from api.domain import EntitiesPage
from api.domain.usage.entities import EnvironmentalImpacts, UsageBucket
from api.infrastructure.postgres import PostgresUsageRepository
from api.tests.integration.factories.sql import KeySQLFactory, UsageSQLFactory, UserSQLFactory

CHAT_COMPLETIONS = "/v1/chat/completions"
EMBEDDINGS = "/v1/embeddings"
DAY = datetime(2026, 8, 1, tzinfo=UTC)
NEXT_DAY = datetime(2026, 8, 2, tzinfo=UTC)
THIRD_DAY = datetime(2026, 8, 3, tzinfo=UTC)


@pytest.fixture
def repository(db_session):
    return PostgresUsageRepository(postgres_session=db_session)


def _window():
    return DAY, THIRD_DAY + timedelta(days=1)


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

    async def test_filters_by_models(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, created=DAY.replace(hour=12), router_name="model-a", prompt_tokens=10, total_tokens=10)
        UsageSQLFactory(user=user, created=DAY.replace(hour=13), router_name="model-b", prompt_tokens=4, total_tokens=4)
        UsageSQLFactory(user=user, created=DAY.replace(hour=14), router_name="model-c", prompt_tokens=7, total_tokens=7)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usage_buckets_page(
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=10,
            models=["model-a", "model-c"],
        )

        assert result.total == 1
        assert result.data[0].prompt_tokens == 17

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
