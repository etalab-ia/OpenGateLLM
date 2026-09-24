from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import select

from api.domain import EntitiesPage
from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage, UsageBucket
from api.infrastructure.postgres import PostgresUsageRepository
from api.infrastructure.postgres.models import Usage as UsageTable
from api.tests.integration.factories.sql import KeySQLFactory, ProviderSQLFactory, UsageSQLFactory, UserSQLFactory

CHAT_COMPLETIONS = "/v1/chat/completions"
EMBEDDINGS = "/v1/embeddings"
DAY = datetime(2026, 8, 1, tzinfo=UTC)
NEXT_DAY = datetime(2026, 8, 2, tzinfo=UTC)
THIRD_DAY = datetime(2026, 8, 3, tzinfo=UTC)


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
def background_tasks():
    return BackgroundTasks()


@pytest.fixture
def repository(db_session, background_tasks):
    return PostgresUsageRepository(postgres_session=db_session, background_tasks=background_tasks)


async def _seed(db_session):
    provider = ProviderSQLFactory()
    key = KeySQLFactory(user=provider.router.user)
    await db_session.flush()
    return key, provider


def _start_record(repository, key, provider, **overrides):
    arguments = {
        "endpoint": ProviderEndpoint.CHAT_COMPLETIONS,
        "model": provider.router.name,
        "user_id": key.user.id,
        "router_id": provider.router.id,
        "router_name": provider.router.name,
        "user_email": key.user.email,
        "key_id": key.id,
        "key_name": key.name,
    }
    return repository.start_record(**(arguments | overrides))


async def _persisted_rows(db_session) -> list[UsageTable]:
    return list((await db_session.scalars(select(UsageTable))).all())


def _window():
    return DAY, THIRD_DAY + timedelta(days=1)


@pytest.mark.asyncio(loop_scope="session")
class TestRecordUsage:
    async def test_persists_the_recorded_row_on_end_record(self, repository, background_tasks, db_session):
        # Arrange
        key, provider = await _seed(db_session)
        request_id = _start_record(repository, key, provider)
        repository.update_record(usage=_usage(), provider_id=provider.id, provider_model_name=provider.model_name)

        # Act
        repository.end_record()
        await background_tasks()

        # Assert
        [row] = await _persisted_rows(db_session)
        assert row.request_id == request_id
        assert row.endpoint == CHAT_COMPLETIONS
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
        assert row.ttft is None
        assert row.created.tzinfo is not None

    async def test_persists_latency_and_ttft(self, repository, background_tasks, db_session):
        # Arrange
        key, provider = await _seed(db_session)
        start = datetime(2026, 9, 21, 10, 0, 0, tzinfo=UTC)
        first_token_at = datetime(2026, 9, 21, 10, 0, 0, 50000, tzinfo=UTC)
        end = datetime(2026, 9, 21, 10, 0, 0, 250000, tzinfo=UTC)
        with patch("api.infrastructure.postgres._postgresusagerepository.datetime") as mock_datetime:
            mock_datetime.now.side_effect = [start, end]
            _start_record(repository, key, provider)
            repository.update_record(usage=_usage(), provider_id=provider.id, provider_model_name=provider.model_name, first_token_at=first_token_at)

        # Act
        repository.end_record()
        await background_tasks()

        # Assert
        [row] = await _persisted_rows(db_session)
        assert row.created == start
        assert row.ttft == 50
        assert row.latency == 250

    async def test_persists_the_failure_status(self, repository, background_tasks, db_session):
        # Arrange
        key, provider = await _seed(db_session)
        _start_record(repository, key, provider)
        repository.fail_record(message="TooBusyModelError", status_code=503)

        # Act
        repository.end_record()
        await background_tasks()

        # Assert
        [row] = await _persisted_rows(db_session)
        assert row.status == 503
        assert row.provider_id is None
        assert row.prompt_tokens is None

    async def test_persists_nothing_when_start_was_not_called(self, repository, background_tasks, db_session):
        # Act
        repository.update_record(usage=_usage(), provider_id=9, provider_model_name="vllm-model")
        repository.fail_record(message="TooBusyModelError", status_code=503)
        repository.end_record()
        await background_tasks()

        # Assert
        assert background_tasks.tasks == []
        assert await _persisted_rows(db_session) == []

    async def test_persists_one_row_per_record(self, repository, background_tasks, db_session):
        # Arrange
        key, provider = await _seed(db_session)

        # Act
        first_request_id = _start_record(repository, key, provider)
        repository.end_record()
        second_request_id = _start_record(repository, key, provider)
        repository.end_record()
        await background_tasks()

        # Assert
        rows = await _persisted_rows(db_session)
        assert sorted(row.request_id for row in rows) == sorted([first_request_id, second_request_id])

    async def test_swallows_persist_errors(self, repository, background_tasks, db_session):
        # Arrange
        key, provider = await _seed(db_session)
        _start_record(repository, key, provider, user_id=key.user.id + 1_000_000)
        repository.end_record()

        # Act / Assert
        await background_tasks()


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
