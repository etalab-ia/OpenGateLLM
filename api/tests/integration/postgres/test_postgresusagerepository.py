from datetime import UTC, datetime, timedelta

import pytest

from api.domain import EntitiesPage
from api.domain.usage.entities import EnvironmentalImpacts, UsageRecord
from api.infrastructure.postgres import PostgresUsageRepository
from api.tests.integration.factories.sql import UsageSQLFactory, UserSQLFactory

CHAT_COMPLETIONS = "/v1/chat/completions"
EMBEDDINGS = "/v1/embeddings"


@pytest.fixture
def repository(db_session):
    return PostgresUsageRepository(postgres_session=db_session)


def _window(*, days_ago: int = 30):
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(days=days_ago)
    return start_time, end_time


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsagesPage:
    async def test_returns_usages_for_user(self, repository, db_session):
        user = UserSQLFactory()
        other_user = UserSQLFactory()
        UsageSQLFactory(user=user, router_name="own-model", token_name="own-key")
        UsageSQLFactory(user=other_user, router_name="other-model")
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert isinstance(result, EntitiesPage)
        assert result.total == 1
        assert len(result.data) == 1
        usage = result.data[0]
        assert isinstance(usage, UsageRecord)
        assert usage.model == "own-model"
        assert usage.key == "own-key"
        assert usage.endpoint == CHAT_COMPLETIONS

    async def test_excludes_non_success_status(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, router_name="ok-model", status=200)
        UsageSQLFactory(user=user, router_name="failed-model", failed=True)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.total == 1
        assert result.data[0].model == "ok-model"

    async def test_filters_by_endpoint(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, router_name="chat-model", endpoint=CHAT_COMPLETIONS)
        UsageSQLFactory(user=user, router_name="embed-model", embeddings=True)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(
            user_id=user.id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=10,
            endpoint=EMBEDDINGS,
        )

        assert result.total == 1
        assert result.data[0].model == "embed-model"
        assert result.data[0].endpoint == EMBEDDINGS

    async def test_filters_by_time_window(self, repository, db_session):
        user = UserSQLFactory()
        now = datetime.now(tz=UTC)
        UsageSQLFactory(user=user, router_name="recent-model", created=now - timedelta(days=1))
        UsageSQLFactory(user=user, router_name="old-model", created=now - timedelta(days=60))
        await db_session.flush()

        result = await repository.get_usages_page(
            user_id=user.id,
            start_time=now - timedelta(days=30),
            end_time=now,
            offset=0,
            limit=10,
        )

        assert result.total == 1
        assert result.data[0].model == "recent-model"

    async def test_maps_null_environmental_impacts_to_zero(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user, kwh=None, kgco2eq=None)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert result.data[0].impacts == EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0)

    async def test_returns_empty_page_when_offset_exceeds_total(self, repository, db_session):
        user = UserSQLFactory()
        UsageSQLFactory(user=user)
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=100, limit=10)

        assert result.data == []
        assert result.total == 1

    async def test_orders_by_created_desc(self, repository, db_session):
        user = UserSQLFactory()
        now = datetime.now(tz=UTC)
        UsageSQLFactory(user=user, router_name="older", created=now - timedelta(hours=2))
        UsageSQLFactory(user=user, router_name="newer", created=now - timedelta(hours=1))
        await db_session.flush()

        start_time, end_time = _window()
        result = await repository.get_usages_page(user_id=user.id, start_time=start_time, end_time=end_time, offset=0, limit=10)

        assert [usage.model for usage in result.data] == ["newer", "older"]
