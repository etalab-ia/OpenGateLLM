from datetime import datetime

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.model.views import ModelView
from api.infrastructure.postgres import PostgresModelQuery
from api.tests.integration.factories.sql import OrganizationSQLFactory, ProviderSQLFactory, RouterSQLFactory, UserSQLFactory

APP_TITLE = "Test App"


@pytest.fixture
def query(db_session):
    return PostgresModelQuery(db_session, APP_TITLE)


@pytest.mark.asyncio(loop_scope="session")
class TestGetModels:
    async def test_returns_a_model_per_router_with_at_least_one_provider(self, query, db_session):
        # Arrange
        router_with_providers = RouterSQLFactory(name="served-router", providers=2)
        RouterSQLFactory(name="empty-router")
        await db_session.flush()

        # Act
        result = await query.get_models()

        # Assert
        assert [model.id for model in result] == ["served-router"]
        assert result[0].router_id == router_with_providers.id

    async def test_returns_the_router_costs_aliases_and_type(self, query, db_session):
        # Arrange
        router = RouterSQLFactory(
            name="detailed-router",
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            alias=["alias1", "alias2"],
            providers=1,
            created=datetime(2024, 5, 17, 10, 30),  # whole second: the query rounds the epoch to an int
        )
        await db_session.flush()

        # Act
        result = await query.get_models()

        # Assert
        assert result == [
            ModelView(
                router_id=router.id,
                id="detailed-router",
                type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
                aliases=["alias1", "alias2"],
                created=int(router.created.timestamp()),
                owned_by=router.user.organization.name,
                max_context_length=router.provider[0].max_context_length,
                costs={"prompt_tokens": 0.001, "completion_tokens": 0.002},
            )
        ]

    async def test_returns_the_max_context_length_of_the_first_provider_of_the_router(self, query, db_session):
        # Arrange
        router = RouterSQLFactory(name="multi-provider-router")
        first_provider = ProviderSQLFactory(router=router, max_context_length=4096)
        ProviderSQLFactory(router=router, max_context_length=8192)
        await db_session.flush()

        # Act
        result = await query.get_models()

        # Assert
        assert result[0].max_context_length == first_provider.max_context_length

    async def test_returns_the_app_title_as_owner_when_the_router_owner_has_no_organization(self, query, db_session):
        # Arrange
        RouterSQLFactory(name="orphan-router", user=UserSQLFactory(organization=None), providers=1)
        await db_session.flush()

        # Act
        result = await query.get_models()

        # Assert
        assert result[0].owned_by == APP_TITLE


@pytest.mark.asyncio(loop_scope="session")
class TestGetModelByNameOrAlias:
    async def test_returns_the_model_when_looked_up_by_name(self, query, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="DINUM")
        router = RouterSQLFactory(name="router-by-name", user=UserSQLFactory(organization=organization), providers=1)
        await db_session.flush()

        # Act
        result = await query.get_model_by_name_or_alias(name="router-by-name")

        # Assert
        assert isinstance(result, ModelView)
        assert result.router_id == router.id
        assert result.id == "router-by-name"
        assert result.owned_by == "DINUM"

    async def test_returns_the_model_when_looked_up_by_alias(self, query, db_session):
        # Arrange
        router = RouterSQLFactory(name="router-by-alias", alias=["lookup-alias"], providers=1)
        await db_session.flush()

        # Act
        result = await query.get_model_by_name_or_alias(name="lookup-alias")

        # Assert
        assert isinstance(result, ModelView)
        assert result.router_id == router.id
        assert result.id == "router-by-alias"

    async def test_returns_model_not_found_when_no_router_matches(self, query, db_session):
        # Act
        result = await query.get_model_by_name_or_alias(name="unknown-router")

        # Assert
        assert result == ModelNotFoundError(name="unknown-router")

    async def test_returns_model_not_found_when_the_router_has_no_provider(self, query, db_session):
        # Arrange
        RouterSQLFactory(name="empty-router")
        await db_session.flush()

        # Act
        result = await query.get_model_by_name_or_alias(name="empty-router")

        # Assert
        assert result == ModelNotFoundError(name="empty-router")
