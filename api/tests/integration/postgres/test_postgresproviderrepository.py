from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from api.domain import SortOrder
from api.domain.key.entities import MASTER_USER_ID
from api.domain.model.entities import Metric, ModelType
from api.domain.provider import Provider, ProviderAlreadyExistsError, ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.entities import ProviderSortField
from api.infrastructure.postgres import PostgresProviderRepository
from api.sql.models import Provider as ProviderTable
from api.tests.integration.factories import (
    ProviderSQLFactory,
    RouterSQLFactory,
    UserSQLFactory,
)

_EXCLUDE = {"id", "created", "updated"}


def _create_provider_args(user, router, **overrides):
    return {
        "user_id": user.id,
        "router_id": router.id,
        "provider_type": ProviderType.ALBERT,
        "url": "http://test.com/",
        "key": "model-key",
        "timeout": 60,
        "model_name": "my-model",
        "model_hosting_zone": ProviderCarbonFootprintZone.FRA,
        "model_total_params": 1000,
        "model_active_params": 2000,
        "qos_metric": Metric.TTFT,
        "qos_limit": 12,
        "vector_size": 10,
        "max_context_length": 20,
        **overrides,
    }


@pytest.fixture
def repository(db_session):
    return PostgresProviderRepository(db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateProvider:
    async def test_create_provider_should_return_created_provider(self, repository, db_session):
        # Arrange
        user = UserSQLFactory(admin_user=True)
        router = RouterSQLFactory(user=user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        # Act
        result = await repository.create_provider(**_create_provider_args(user, router))

        # Assert
        expected = Provider(
            id=result.id,
            router_id=router.id,
            user_id=user.id,
            type=ProviderType.ALBERT,
            url="http://test.com/",
            key="model-key",
            timeout=60,
            model_name="my-model",
            model_hosting_zone=ProviderCarbonFootprintZone.FRA,
            model_total_params=1000,
            model_active_params=2000,
            qos_metric=Metric.TTFT,
            qos_limit=12,
            vector_size=10,
            max_context_length=20,
        )
        assert result.model_dump(exclude=_EXCLUDE) == expected.model_dump(exclude=_EXCLUDE)

    async def test_create_provider_should_return_provider_already_exists_when_same_url_name_and_router_are_used(self, repository, db_session):
        # Arrange
        user = UserSQLFactory(admin_user=True)
        router = RouterSQLFactory(user=user, type=ModelType.TEXT_GENERATION)
        ProviderSQLFactory(type=ProviderType.ALBERT, url="http://test.com/", model_name="duplicate-provider", router=router)
        await db_session.flush()

        # Act
        result = await repository.create_provider(**_create_provider_args(user, router, model_name="duplicate-provider"))

        # Assert
        assert isinstance(result, ProviderAlreadyExistsError)
        assert result.router_id == router.id
        assert result.url == "http://test.com/"
        assert result.model_name == "duplicate-provider"


@pytest.mark.asyncio(loop_scope="session")
class TestGetOneProvider:
    async def test_get_one_provider_should_return_provider_when_it_exists(self, repository, db_session):
        # Arrange
        provider = ProviderSQLFactory(type=ProviderType.ALBERT, url="http://test.com/", model_name="target-provider", qos_metric=None)
        await db_session.flush()

        # Act
        result = await repository.get_one_provider(provider.id)

        # Assert
        assert isinstance(result, Provider)
        assert result.id == provider.id
        assert result.router_id == provider.router_id
        assert result.user_id == provider.user_id
        assert result.type == ProviderType.ALBERT
        assert result.url == "http://test.com/"
        assert result.model_name == "target-provider"
        assert result.max_context_length == provider.max_context_length
        assert result.vector_size == provider.vector_size

    async def test_get_one_provider_should_return_none_when_provider_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_one_provider(provider_id=999999)

        # Assert
        assert result is None

    async def test_get_one_provider_should_map_null_user_id_to_master_user_id(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(user=None)
        provider = ProviderSQLFactory(router=router, user=None)
        await db_session.flush()

        # Act
        result = await repository.get_one_provider(provider.id)

        # Assert
        assert isinstance(result, Provider)
        assert result.user_id == MASTER_USER_ID


@pytest.mark.asyncio(loop_scope="session")
class TestGetProvidersPage:
    async def test_returns_correct_page_with_limit_and_offset(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        ProviderSQLFactory(router=router, model_name="provider_a")
        ProviderSQLFactory(router=router, model_name="provider_b")
        ProviderSQLFactory(router=router, model_name="provider_c")
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(router_id=None, limit=2, offset=0, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC)

        # Assert
        assert result.total == 3
        assert len(result.data) == 2

    async def test_total_is_consistent_across_pages(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        for i in range(6):
            ProviderSQLFactory(router=router, model_name=f"provider_{i}")
        await db_session.flush()

        # Act
        first_page = await repository.get_providers_page(router_id=None, limit=4, offset=0)
        second_page = await repository.get_providers_page(router_id=None, limit=4, offset=4)

        # Assert
        assert first_page.total == second_page.total
        assert first_page.total == 6
        assert len(second_page.data) == 2

    async def test_sort_by_id_asc(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        ProviderSQLFactory(id=4003, router=router, model_name="provider_c")
        ProviderSQLFactory(id=4001, router=router, model_name="provider_a")
        ProviderSQLFactory(id=4002, router=router, model_name="provider_b")
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(router_id=None, limit=10, offset=0, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC)

        # Assert
        returned_ids = [p.id for p in result.data]
        assert returned_ids == [4001, 4002, 4003]

    async def test_sort_by_model_name_asc(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        ProviderSQLFactory(router=router, model_name="provider_c")
        ProviderSQLFactory(router=router, model_name="provider_a")
        ProviderSQLFactory(router=router, model_name="provider_b")
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(
            router_id=None, limit=10, offset=0, sort_by=ProviderSortField.MODEL_NAME, sort_order=SortOrder.ASC
        )

        # Assert
        returned_names = [p.model_name for p in result.data]
        assert returned_names == ["provider_a", "provider_b", "provider_c"]

    async def test_sort_by_created_date_desc(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        ProviderSQLFactory(router=router, model_name="oldest", created=datetime.now() - timedelta(days=10))
        ProviderSQLFactory(router=router, model_name="newest", created=datetime.now())
        ProviderSQLFactory(router=router, model_name="middle", created=datetime.now() - timedelta(hours=1))
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(router_id=None, limit=10, offset=0, sort_by=ProviderSortField.CREATED, sort_order=SortOrder.DESC)

        # Assert
        returned_names = [p.model_name for p in result.data]
        assert returned_names == ["newest", "middle", "oldest"]

    async def test_returns_empty_page_when_offset_exceeds_total(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory()
        ProviderSQLFactory(router=router)
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(router_id=None, limit=10, offset=100)

        # Assert
        assert result.data == []
        assert result.total == 1

    async def test_filter_by_router_id_returns_only_providers_for_that_router(self, repository, db_session):
        # Arrange
        router_1 = RouterSQLFactory()
        router_2 = RouterSQLFactory()
        ProviderSQLFactory(router=router_1, model_name="provider_r1_1")
        ProviderSQLFactory(router=router_1, model_name="provider_r1_2")
        ProviderSQLFactory(router=router_2, model_name="provider_r2_1")
        await db_session.flush()

        # Act
        result = await repository.get_providers_page(router_id=router_1.id, limit=10, offset=0)

        # Assert
        assert result.total == 2
        assert len(result.data) == 2
        assert all(provider.router_id == router_1.id for provider in result.data)


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteProvider:
    async def test_delete_provider_should_return_the_deleted_provider_when_provider_exists(self, repository, db_session):
        # Arrange
        provider = ProviderSQLFactory(model_name="provider_to_delete")
        await db_session.flush()

        # Act
        result = await repository.delete_provider(provider.id)

        # Assert
        assert isinstance(result, Provider)
        assert result.id == provider.id
        assert result.model_name == "provider_to_delete"

    async def test_delete_provider_should_return_none_when_provider_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.delete_provider(provider_id=999999)

        # Assert
        assert result is None

    async def test_delete_provider_should_remove_provider_from_database(self, repository, db_session):
        # Arrange
        provider = ProviderSQLFactory(model_name="provider_to_remove")
        await db_session.flush()

        # Act
        await repository.delete_provider(provider.id)

        # Assert
        await db_session.flush()
        provider_after_delete = (await db_session.execute(select(ProviderTable).where(ProviderTable.id == provider.id))).scalar_one_or_none()
        assert provider_after_delete is None
