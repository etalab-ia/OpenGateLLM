import pytest
import respx
from sqlalchemy import select

from api.domain.model.entities import ModelType as RouterType
from api.domain.provider.entities import ProviderType
from api.schemas.core.configuration import Configuration, Dependencies, Model, ModelProvider, Settings
from api.sql.models import Provider, Router
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_models_responses
from api.tests.integration.factories.albert import AlbertModelResponseFactory, AlbertModelsResponseFactory
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.utils.context import global_context
from api.utils.lifespan import bootstrap_models

DEFAULT_MODEL_ID = "test/my-model"
DEFAULT_MAX_CONTEXT_LENGTH = 4096


@pytest.fixture
def bootstrap_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(app_title="test"),
        dependencies=Dependencies.model_construct(sentry=None),
        models=[],
    )


@pytest.fixture(autouse=True)
def _set_global_redis_pool(test_redis_pool):
    previous = global_context.redis_pool
    global_context.redis_pool = test_redis_pool
    try:
        yield
    finally:
        global_context.redis_pool = previous


@pytest.mark.asyncio(loop_scope="session")
class TestBootstrapModels:
    @respx.mock
    async def test_creates_router_and_provider_when_no_router_exists(self, db_session, bootstrap_configuration):
        # Arrange
        admin = UserSQLFactory(admin_user=True)
        await db_session.flush()

        bootstrap_configuration.models = [
            Model(
                name="my-router",
                type=RouterType.TEXT_GENERATION,
                providers=[ModelProvider(type=ProviderType.ALBERT, url=DEFAULT_PROVIDER_URL, model_name=DEFAULT_MODEL_ID)],
            )
        ]
        mock_models_responses(
            respx_mock=respx,
            provider_type=ProviderType.ALBERT,
            body=AlbertModelsResponseFactory(
                data=[AlbertModelResponseFactory(model_id=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH)],
            ),
            status_code=AlbertModelsResponseFactory._status_code,
        )

        # Act
        result = await bootstrap_models(
            configuration=bootstrap_configuration,
            postgres_session=db_session,
            bootstrap_admin_user_id=admin.id,
        )
        await db_session.flush()

        # Assert
        assert result == 1

        router = (await db_session.execute(select(Router).where(Router.name == "my-router"))).scalar_one_or_none()
        assert router is not None
        assert router.user_id == admin.id
        assert router.type == RouterType.TEXT_GENERATION

        provider = (await db_session.execute(select(Provider).where(Provider.router_id == router.id))).scalar_one_or_none()
        assert provider is not None
        assert provider.model_name == DEFAULT_MODEL_ID
        assert provider.max_context_length == DEFAULT_MAX_CONTEXT_LENGTH

    async def test_skips_when_routers_already_exist(self, db_session, bootstrap_configuration):
        # Arrange
        admin = UserSQLFactory(admin_user=True)
        existing_router = RouterSQLFactory(user=admin)
        await db_session.flush()

        bootstrap_configuration.models = [
            Model(
                name="another-router",
                type=RouterType.TEXT_GENERATION,
                providers=[ModelProvider(type=ProviderType.ALBERT, url=DEFAULT_PROVIDER_URL, model_name=DEFAULT_MODEL_ID)],
            )
        ]

        # Act
        result = await bootstrap_models(
            configuration=bootstrap_configuration,
            postgres_session=db_session,
            bootstrap_admin_user_id=admin.id,
        )

        # Assert
        assert result == 1

        routers = (await db_session.execute(select(Router))).scalars().all()
        assert len(routers) == 1
        assert routers[0].id == existing_router.id

    async def test_returns_zero_when_no_models_to_create(self, db_session, bootstrap_configuration):
        # Arrange
        admin = UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        result = await bootstrap_models(
            configuration=bootstrap_configuration,
            postgres_session=db_session,
            bootstrap_admin_user_id=admin.id,
        )

        # Assert
        assert result == 0
        routers = (await db_session.execute(select(Router))).scalars().all()
        assert routers == []

    async def test_raises_runtime_error_when_router_name_is_duplicated(self, db_session, bootstrap_configuration):
        # Arrange
        admin = UserSQLFactory(admin_user=True)
        await db_session.flush()

        bootstrap_configuration.models = [
            Model(
                name="duplicate",
                type=RouterType.TEXT_GENERATION,
                providers=[ModelProvider(type=ProviderType.ALBERT, url=DEFAULT_PROVIDER_URL, model_name="model-a")],
            ),
            Model(
                name="duplicate",
                type=RouterType.TEXT_GENERATION,
                providers=[ModelProvider(type=ProviderType.ALBERT, url=DEFAULT_PROVIDER_URL, model_name="model-b")],
            ),
        ]

        # Act & Assert
        with pytest.raises(RuntimeError, match="Router name or alias is already taken"):
            await bootstrap_models(
                configuration=bootstrap_configuration,
                postgres_session=db_session,
                bootstrap_admin_user_id=admin.id,
            )

        routers = (await db_session.execute(select(Router))).scalars().all()
        assert routers == []

    @respx.mock
    async def test_raises_runtime_error_when_provider_not_reachable(self, db_session, bootstrap_configuration):
        # Arrange
        admin = UserSQLFactory(admin_user=True)
        await db_session.flush()

        bootstrap_configuration.models = [
            Model(
                name="my-router",
                type=RouterType.TEXT_GENERATION,
                providers=[ModelProvider(type=ProviderType.ALBERT, url=DEFAULT_PROVIDER_URL, model_name=DEFAULT_MODEL_ID)],
            )
        ]
        mock_models_responses(
            respx_mock=respx,
            provider_type=ProviderType.ALBERT,
            body={"detail": "Internal Server Error"},
            status_code=500,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="not reachable"):
            await bootstrap_models(
                configuration=bootstrap_configuration,
                postgres_session=db_session,
                bootstrap_admin_user_id=admin.id,
            )

        routers = (await db_session.execute(select(Router))).scalars().all()
        assert routers == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
