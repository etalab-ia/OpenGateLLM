from datetime import datetime, timedelta

import pytest

from api.domain.key.entities import MASTER_USER_ID
from api.domain.model import ModelType as RouterType
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterSortField, SortOrder
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.infrastructure.postgres import PostgresRouterRepository
from api.tests.integration.factories import OrganizationSQLFactory, RouterSQLFactory, UserSQLFactory


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
        user_1 = UserSQLFactory()
        user_2 = UserSQLFactory()

        router_1 = RouterSQLFactory(
            user=user_1,
            name="router_1",
            type=RouterType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            providers=2,
            alias=["alias1", "alias2"],
        )
        router_2 = RouterSQLFactory(
            user=user_1, name="router_2", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0, providers=1
        )
        router_3 = RouterSQLFactory(
            user=user_2, name="router_3", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, cost_prompt_tokens=0.0, cost_completion_tokens=0.0, providers=1
        )

        # Act
        await db_session.flush()
        result_routers = await repository.get_all_routers()

        # Assert
        assert len(result_routers) == 3
        router_names = {r.name for r in result_routers}
        assert router_names == {router_1.name, router_2.name, router_3.name}

        result_router_1 = result_routers[0]
        first_provider_router_1 = router_1.provider[0]
        assert result_router_1.type == RouterType.TEXT_GENERATION
        assert result_router_1.providers == 2
        assert result_router_1.cost_prompt_tokens == 0.001
        assert result_router_1.cost_completion_tokens == 0.002
        assert result_router_1.max_context_length == first_provider_router_1.max_context_length
        assert result_router_1.vector_size == first_provider_router_1.vector_size
        assert result_router_1.aliases == ["alias1", "alias2"]

    async def test_get_all_routers_should_return_routers_with_master_id_user(self, repository, db_session):
        # Arrange
        RouterSQLFactory(
            user=None, name="router_1", type=RouterType.TEXT_GENERATION, cost_prompt_tokens=0.001, cost_completion_tokens=0.002, providers=2
        )

        # Act
        await db_session.flush()
        result_routers = await repository.get_all_routers()

        # Assert
        router_user_id = result_routers[0].user_id
        assert router_user_id == MASTER_USER_ID


@pytest.mark.asyncio(loop_scope="session")
class TestGetAllAliases:
    async def test_get_all_aliases_should_return_all_aliases(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="DINUM")
        user_1 = UserSQLFactory(organization=organization)
        user_2 = UserSQLFactory(organization=organization)
        user_3 = UserSQLFactory()

        router_1 = RouterSQLFactory(
            user=user_1,
            alias=[
                "alias1_m1",
                "alias2_m1",
            ],
        )
        router_2 = RouterSQLFactory(user=user_1, alias=["alias1_m2"])
        router_3 = RouterSQLFactory(user=user_2, alias=["alias1_m3"])
        router_4 = RouterSQLFactory(user=user_3, alias=["alias1_m4", "alias2_m4"])

        # Act
        await db_session.flush()
        aliases = await repository.get_aliases_grouped_by_router()
        # Assert
        assert aliases == {
            router_1.id: ["alias1_m1", "alias2_m1"],
            router_2.id: ["alias1_m2"],
            router_3.id: ["alias1_m3"],
            router_4.id: ["alias1_m4", "alias2_m4"],
        }


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRouter:
    async def test_create_router_should_return_created_router_without_alias(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="test-router",
            router_type=RouterType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, Router)
        assert result.name == "test-router"
        assert result.type == RouterType.TEXT_GENERATION
        assert result.load_balancing_strategy == RouterLoadBalancingStrategy.SHUFFLE
        assert result.cost_prompt_tokens == 0.001
        assert result.cost_completion_tokens == 0.002
        assert result.user_id == user.id
        assert result.aliases == []
        assert result.providers == 0
        assert result.id is not None
        assert result.created is not None
        assert result.updated is not None

    async def test_create_router_should_return_router_name_already_exists_when_name_is_duplicate(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="duplicate-router")
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="duplicate-router",
            router_type=RouterType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "duplicate-router"

    async def test_create_router_with_master_user_id_should_set_db_user_id_to_null(self, repository, db_session):
        # Arrange
        master_user_id = 0

        # Act
        result = await repository.create_router(
            name="master-router",
            router_type=RouterType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=master_user_id,
        )

        # Assert
        assert isinstance(result, Router)
        assert result.user_id == master_user_id
        assert result.name == "master-router"

    async def test_create_router_with_aliases_should_insert_aliases(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="router-with-aliases",
            router_type=RouterType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
            aliases=["alias1", "alias2"],
        )

        # Assert
        assert isinstance(result, Router)
        assert result.name == "router-with-aliases"
        assert result.aliases == ["alias1", "alias2"]

        # Verify aliases are persisted in DB
        persisted_aliases = await repository.get_aliases(["alias1", "alias2"])
        assert set(persisted_aliases) == {"alias1", "alias2"}

    async def test_create_router_should_return_router_alias_already_exists_when_one_alias_is_duplicate(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        duplicate_alias = "duplicate-alias"
        RouterSQLFactory(user=user, name="router-with-aliases", alias=[duplicate_alias])
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="router",
            router_type=RouterType.TEXT_GENERATION,
            aliases=[duplicate_alias],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["duplicate-alias"]

    async def test_create_router_should_return_router_alias_already_exists_when_several_aliases_are_duplicate(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        duplicate_aliases = ["duplicate-alias", "duplicate-alias-2"]
        RouterSQLFactory(user=user, name="router-with-aliases", alias=duplicate_aliases)
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="router",
            router_type=RouterType.TEXT_GENERATION,
            aliases=duplicate_aliases,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["duplicate-alias", "duplicate-alias-2"]


@pytest.mark.asyncio(loop_scope="session")
class TestGetOrganizationName:
    async def test_get_organization_name_should_return_the_organization_name_from_the_given_id(self, repository, db_session):
        # Arrange
        organization_name = "DINUM"
        dinum_organization = OrganizationSQLFactory(name=organization_name)
        user_with_organization = UserSQLFactory(organization=dinum_organization)
        await db_session.flush()

        # Act
        actual_organization_name = await repository.get_organization_name(user_id=user_with_organization.id)
        # Assert
        assert actual_organization_name == organization_name

    async def test_get_organization_name_should_return_the_app_title_when_the_user_has_no_organization(self, repository, db_session, app_title):
        # Arrange
        user_without_organiztion = UserSQLFactory(organization=None)
        await db_session.flush()

        # Act
        actual_organization_name = await repository.get_organization_name(user_id=user_without_organiztion.id)
        # Assert
        assert actual_organization_name == app_title


@pytest.mark.asyncio(loop_scope="session")
class TestGetRoutersPage:
    async def test_returns_correct_page_with_limit_and_offset(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_a")
        RouterSQLFactory(user=user, name="router_b")
        RouterSQLFactory(user=user, name="router_c")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=2, offset=0, sort_by=RouterSortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        assert result.total == 3
        assert len(result.data) == 2
        assert result.data[0].name == "router_a"
        assert result.data[1].name == "router_b"

    async def test_total_is_consistent_across_pages(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_a")
        RouterSQLFactory(user=user, name="router_b")
        RouterSQLFactory(user=user, name="router_c")
        RouterSQLFactory(user=user, name="router_d")
        RouterSQLFactory(user=user, name="router_e")
        RouterSQLFactory(user=user, name="router_f")
        await db_session.flush()

        # Act
        first_page = await repository.get_routers_page(limit=4, offset=0)
        second_page = await repository.get_routers_page(limit=4, offset=4)

        # Assert
        assert first_page.total == second_page.total
        assert len(second_page.data) == 2

    async def test_sort_by_name_asc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_c")
        RouterSQLFactory(user=user, name="router_a")
        RouterSQLFactory(user=user, name="router_b")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=RouterSortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        returned_names = [r.name for r in result.data]
        assert returned_names == ["router_a", "router_b", "router_c"]

    async def test_sort_by_name_desc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_c")
        RouterSQLFactory(user=user, name="router_a")
        RouterSQLFactory(user=user, name="router_b")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=RouterSortField.NAME, sort_order=SortOrder.DESC)

        # Assert
        returned_names = [r.name for r in result.data]

        assert returned_names == ["router_c", "router_b", "router_a"]

    async def test_returns_empty_page_when_offset_exceeds_total(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_a")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=100)

        # Assert
        assert result.data == []

    async def test_sort_by_id_asc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(id=1235, user=user, name="router_a")
        RouterSQLFactory(id=1233, user=user, name="router_b")
        RouterSQLFactory(id=1234, user=user, name="router_c")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=RouterSortField.ID, sort_order=SortOrder.ASC)

        # Assert
        returned_ids = [r.id for r in result.data]
        assert returned_ids == [1233, 1234, 1235]

    async def test_sort_by_created_date_desc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(id=1233, user=user, name="oldest", created=datetime.now() - timedelta(days=10))
        RouterSQLFactory(id=1235, user=user, name="newest", created=datetime.now())
        RouterSQLFactory(id=1234, user=user, name="middle", created=datetime.now() - timedelta(hours=1))
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=RouterSortField.CREATED, sort_order=SortOrder.DESC)

        # Assert
        returned_names = [r.name for r in result.data]
        assert returned_names == ["newest", "middle", "oldest"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
