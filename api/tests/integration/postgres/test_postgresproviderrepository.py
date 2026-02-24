import pytest

from api.domain.model.entities import Metric, ModelType
from api.domain.provider import Provider, ProviderAlreadyExistsError, ProviderCarbonFootprintZone, ProviderType
from api.infrastructure.postgres import PostgresProviderRepository
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
