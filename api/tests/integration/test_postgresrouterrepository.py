import pytest

from api.domain.router.entities import ModelType
from api.infrastructure.postgres import PostgresRouterRepository
from api.tests.integration.factories import (
    OrganizationFactory,
    ProviderFactory,
    RouterAliasFactory,
    RouterFactory,
    UserFactory,
)


@pytest.fixture
def app_title():
    return "Test App"


@pytest.fixture
def repository(db_session, app_title):
    return PostgresRouterRepository(db_session, app_title)


@pytest.mark.asyncio(loop_scope="session")
class TestGetAllRouters:
    async def test_get_all_routers_should_return_all_routers(self, repository, db_session):
        # Arrange
        user_1 = UserFactory()
        user_2 = UserFactory()

        router_1 = RouterFactory(user=user_1, name="router_1", type=ModelType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002)
        router_2 = RouterFactory(
            user=user_1, name="router_2", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        router_3 = RouterFactory(
            user=user_2, name="router_3", type=ModelType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0
        )
        ProviderFactory(router=router_1, user=user_1, model_name="m1", max_context_length=2048, vector_size=1536)
        ProviderFactory(router=router_1, user=user_1, model_name="m2", max_context_length=128000, vector_size=384)
        ProviderFactory(router=router_2, user=user_1, model_name="m3")
        ProviderFactory(router=router_3, user=user_2, model_name="m4")

        # Act
        await db_session.flush()
        result_routers = await repository.get_all_routers()

        # Assert
        assert len(result_routers) == 3
        router_names = {r.name for r in result_routers}
        assert router_names == {router_1.name, router_2.name, router_3.name}

        r1 = next(r for r in result_routers if r.name == "router_1")
        assert r1.type == ModelType.TEXT_GENERATION
        assert r1.providers == 2
        assert r1.cost_prompt_tokens == 0.001
        assert r1.cost_completion_tokens == 0.002
        assert r1.max_context_length == 2048
        assert r1.vector_size == 1536


@pytest.mark.asyncio(loop_scope="session")
class TestGetAllAliases:
    async def test_get_all_aliases_should_return_all_aliases(self, repository, db_session):
        # Arrange
        organization = OrganizationFactory(name="DINUM")
        user_1 = UserFactory(organization=organization)
        user_2 = UserFactory(organization=organization)
        user_3 = UserFactory()

        router_1 = RouterFactory(user=user_1)
        router_2 = RouterFactory(user=user_1)
        router_3 = RouterFactory(user=user_2)
        router_4 = RouterFactory(user=user_3)

        RouterAliasFactory(router=router_1, value="alias1_m1")
        RouterAliasFactory(router=router_1, value="alias2_m1")
        RouterAliasFactory(router=router_2, value="alias1_m2")
        RouterAliasFactory(router=router_3, value="alias1_m3")
        RouterAliasFactory(router=router_4, value="alias1_m4")
        RouterAliasFactory(router=router_4, value="alias2_m4")
        await db_session.flush()
        # Act
        aliases = await repository.get_all_aliases()
        # Assert
        assert aliases == {
            router_1.id: ["alias1_m1", "alias2_m1"],
            router_2.id: ["alias1_m2"],
            router_3.id: ["alias1_m3"],
            router_4.id: ["alias1_m4", "alias2_m4"],
        }


@pytest.mark.asyncio(loop_scope="session")
class TestGetOrganizationName:
    async def test_get_organization_name_should_return_the_organization_name_from_the_given_id(self, repository, db_session):
        # Arrange
        organization_name = "DINUM"
        dinum_organization = OrganizationFactory(name=organization_name)
        user_with_organization = UserFactory(organization=dinum_organization)
        await db_session.flush()

        # Act
        actual_organization_name = await repository.get_organization_name(user_id=user_with_organization.id)
        # Assert
        assert actual_organization_name == organization_name

    async def test_get_organization_name_should_return_the_app_title_when_the_user_has_no_organization(self, repository, db_session, app_title):
        # Arrange
        user_without_organiztion = UserFactory(organization=None)
        await db_session.flush()

        # Act
        actual_organization_name = await repository.get_organization_name(user_id=user_without_organiztion.id)
        # Assert
        assert actual_organization_name == app_title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
