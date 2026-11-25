from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from api.domain import SortField, SortOrder
from api.domain.router.entities import Router, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.infrastructure.postgres import PostgresRouterRepository
from api.infrastructure.postgres.models import Provider as ProviderTable
from api.infrastructure.postgres.models import Router as RouterTable
from api.infrastructure.postgres.models import RouterAlias as RouterAliasTable
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory


def to_router_domain(router_sql, aliases: list[str] | None = None) -> Router:
    return Router(
        id=router_sql.id,
        name=router_sql.name,
        user_id=router_sql.user_id,
        type=RouterType(router_sql.type),
        aliases=aliases or [],
        qos_retries_before_reject=router_sql.qos_retries_before_reject,
        cost_prompt_tokens=router_sql.cost_prompt_tokens or 0.0,
        cost_completion_tokens=router_sql.cost_completion_tokens or 0.0,
        providers=[],
        created=int(router_sql.created.timestamp()),
        updated=int(router_sql.updated.timestamp()),
    )


@pytest.fixture
def repository(db_session):
    return PostgresRouterRepository(db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetAllRouters:
    async def test_should_return_every_router_with_its_own_aliases_and_providers(self, repository, db_session):
        # Arrange
        router_1 = RouterSQLFactory(
            name="router_1",
            type=RouterType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            alias=["alias1", "alias2"],
        )
        provider_1 = ProviderSQLFactory(router=router_1, model_name="model_1", qos_limit=10, key="secret")
        provider_2 = ProviderSQLFactory(router=router_1, model_name="model_2", qos_limit=None)
        router_2 = RouterSQLFactory(name="router_2", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, alias=["alias3", "alias4"])
        provider_3 = ProviderSQLFactory(router=router_2, model_name="model_3")
        router_3 = RouterSQLFactory(name="router_3", type=RouterType.TEXT_CLASSIFICATION)
        await db_session.flush()

        # Act
        result = await repository.get_all_routers()

        # Assert
        assert [router.id for router in result] == [router_1.id, router_2.id, router_3.id]
        assert [router.name for router in result] == ["router_1", "router_2", "router_3"]
        assert [router.type for router in result] == [
            RouterType.TEXT_GENERATION,
            RouterType.TEXT_EMBEDDINGS_INFERENCE,
            RouterType.TEXT_CLASSIFICATION,
        ]
        assert [router.aliases for router in result] == [["alias1", "alias2"], ["alias3", "alias4"], []]
        assert [[provider.id for provider in router.providers] for router in result] == [[provider_1.id, provider_2.id], [provider_3.id], []]

        assert result[0].cost_prompt_tokens == 0.001
        assert result[0].cost_completion_tokens == 0.002
        assert result[0].providers[0].qos_limit == 10
        assert result[0].providers[0].key == "secret"
        assert result[0].providers[1].qos_limit is None


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
            qos_retries_before_reject=4,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, Router)
        assert result.name == "test-router"
        assert result.type == RouterType.TEXT_GENERATION
        assert result.qos_retries_before_reject == 4
        assert result.cost_prompt_tokens == 0.001
        assert result.cost_completion_tokens == 0.002
        assert result.user_id == user.id
        assert result.aliases == []
        assert result.providers == []
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
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "duplicate-router"

    async def test_create_router_with_aliases_should_insert_aliases(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        await db_session.flush()

        # Act
        result = await repository.create_router(
            name="router-with-aliases",
            router_type=RouterType.TEXT_GENERATION,
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
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=user.id,
        )

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["duplicate-alias", "duplicate-alias-2"]


@pytest.mark.asyncio(loop_scope="session")
class TestGetRoutersPage:
    async def test_should_return_the_requested_page_when_routers_have_several_providers(self, repository, db_session):
        # Arrange
        RouterSQLFactory(name="router_a", providers=2)
        RouterSQLFactory(name="router_b", providers=2)
        RouterSQLFactory(name="router_c", providers=2)
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=2, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.ASC)

        # Assert
        assert result.total == 3
        assert [router.name for router in result.data] == ["router_a", "router_b"]

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
        assert first_page.total == 6
        assert len(second_page.data) == 2

    async def test_sort_by_name_asc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="router_c")
        RouterSQLFactory(user=user, name="router_a")
        RouterSQLFactory(user=user, name="router_b")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.ASC)

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
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=SortField.NAME, sort_order=SortOrder.DESC)

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
        assert result.total == 1

    async def test_sort_by_id_asc(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(id=1235, user=user, name="router_a")
        RouterSQLFactory(id=1233, user=user, name="router_b")
        RouterSQLFactory(id=1234, user=user, name="router_c")
        await db_session.flush()

        # Act
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=SortField.ID, sort_order=SortOrder.ASC)

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
        result = await repository.get_routers_page(limit=10, offset=0, sort_by=SortField.CREATED, sort_order=SortOrder.DESC)

        # Assert
        returned_names = [r.name for r in result.data]
        assert returned_names == ["newest", "middle", "oldest"]


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouterById:
    async def test_should_return_the_router_with_its_aliases_and_providers_when_it_exists(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(
            name="router_by_id",
            type=RouterType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            alias=["alias1", "alias2"],
        )
        provider_1 = ProviderSQLFactory(router=router, model_name="model_1")
        provider_2 = ProviderSQLFactory(router=router, model_name="model_2")
        await db_session.flush()

        # Act
        result = await repository.get_router_by_id(router.id)

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.name == "router_by_id"
        assert result.type == RouterType.TEXT_GENERATION
        assert result.cost_prompt_tokens == 0.001
        assert result.cost_completion_tokens == 0.002
        assert result.aliases == ["alias1", "alias2"]
        assert [provider.id for provider in result.providers] == [provider_1.id, provider_2.id]

    async def test_get_router_by_id_should_return_router_not_found_when_router_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_router_by_id(router_id=999999)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 999999

    async def test_get_router_by_id_should_return_router_without_aliases_when_none_set(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(name="router_no_alias", alias=[])
        await db_session.flush()

        # Act
        result = await repository.get_router_by_id(router.id)

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.aliases == []


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouterByNameOrAlias:
    async def test_get_router_by_name_or_alias_should_return_router_when_lookup_by_name(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(
            name="router_by_name",
            type=RouterType.TEXT_GENERATION,
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
            alias=["alias1", "alias2"],
        )
        provider_1 = ProviderSQLFactory(router=router, model_name="model_1")
        provider_2 = ProviderSQLFactory(router=router, model_name="model_2")
        await db_session.flush()

        # Act
        result = await repository.get_router_by_name_or_alias("router_by_name")

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.name == "router_by_name"
        assert result.type == RouterType.TEXT_GENERATION
        assert result.cost_prompt_tokens == 0.001
        assert result.cost_completion_tokens == 0.002
        assert [provider.id for provider in result.providers] == [provider_1.id, provider_2.id]
        assert result.aliases == ["alias1", "alias2"]

    async def test_should_return_the_router_with_its_aliases_and_providers_when_looked_up_by_alias(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(name="router_by_alias", alias=["lookup_alias", "other_alias"])
        provider_1 = ProviderSQLFactory(router=router, model_name="model_1")
        provider_2 = ProviderSQLFactory(router=router, model_name="model_2")
        RouterSQLFactory(name="other-router", providers=1)
        await db_session.flush()

        # Act
        result = await repository.get_router_by_name_or_alias("lookup_alias")

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.name == "router_by_alias"
        assert result.aliases == ["lookup_alias", "other_alias"]
        assert [provider.id for provider in result.providers] == [provider_1.id, provider_2.id]

    async def test_get_router_by_name_or_alias_should_return_router_not_found_when_name_or_alias_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_router_by_name_or_alias("unknown-router")

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.name == "unknown-router"

    async def test_get_router_by_name_or_alias_should_return_router_without_aliases_when_none_set(self, repository, db_session):
        # Arrange
        router = RouterSQLFactory(name="router_no_alias_lookup", alias=[])
        await db_session.flush()

        # Act
        result = await repository.get_router_by_name_or_alias("router_no_alias_lookup")

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.aliases == []


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteRouter:
    async def test_delete_router_should_return_the_deleted_router_when_router_exists(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router_to_delete", alias=["alias1"])
        await db_session.flush()

        # Act
        result = await repository.delete_router(router.id)

        # Assert
        assert isinstance(result, Router)
        assert result.id == router.id
        assert result.name == "router_to_delete"
        assert result.aliases == ["alias1"]

    async def test_delete_router_should_return_router_not_found_when_router_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.delete_router(router_id=999999)

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 999999

    async def test_delete_router_should_delete_cascade_router_aliases_and_providers_from_database(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router_to_delete", alias=["alias1"], providers=3)
        await db_session.flush()

        # Act
        await repository.delete_router(router.id)

        # Assert
        await db_session.flush()
        router_after_delete = (await db_session.execute(select(RouterTable).where(RouterTable.id == router.id))).scalar_one_or_none()
        aliases = (await db_session.execute(select(RouterAliasTable).where(RouterAliasTable.router_id == router.id))).scalars().all()
        providers = (await db_session.execute(select(ProviderTable).where(ProviderTable.router_id == router.id))).scalars().all()
        assert router_after_delete is None
        assert aliases == []
        assert providers == []


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteAllRouters:
    async def test_should_return_the_deleted_routers_with_their_aliases_and_providers(self, repository, db_session):
        # Arrange
        router_1 = RouterSQLFactory(name="router_1", alias=["alias1"])
        provider_1 = ProviderSQLFactory(router=router_1, model_name="model_1")
        router_2 = RouterSQLFactory(name="router_2", alias=["alias2"])
        provider_2 = ProviderSQLFactory(router=router_2, model_name="model_2")
        provider_3 = ProviderSQLFactory(router=router_2, model_name="model_3")
        await db_session.flush()

        # Act
        result = await repository.delete_all_routers()

        # Assert
        assert [router.id for router in result] == [router_1.id, router_2.id]
        assert [router.aliases for router in result] == [["alias1"], ["alias2"]]
        assert [[provider.id for provider in router.providers] for router in result] == [[provider_1.id], [provider_2.id, provider_3.id]]

    async def test_delete_all_routers_should_delete_cascade_router_aliases_and_providers_from_database(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router_1 = RouterSQLFactory(user=user, name="router_1", alias=["alias1"], providers=2)
        router_2 = RouterSQLFactory(user=user, name="router_2", alias=["alias2"], providers=1)
        await db_session.flush()
        router_ids = [router_1.id, router_2.id]

        # Act
        await repository.delete_all_routers()

        # Assert
        await db_session.flush()
        routers_after_delete = (await db_session.execute(select(RouterTable).where(RouterTable.id.in_(router_ids)))).scalars().all()
        aliases = (await db_session.execute(select(RouterAliasTable).where(RouterAliasTable.router_id.in_(router_ids)))).scalars().all()
        providers = (await db_session.execute(select(ProviderTable).where(ProviderTable.router_id.in_(router_ids)))).scalars().all()
        assert routers_after_delete == []
        assert aliases == []
        assert providers == []


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateRouter:
    async def test_update_router_should_return_router_with_updated_name(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="original-name")
        await db_session.flush()

        # Act
        result = await repository.update_router(to_router_domain(router).with_name("updated-name"))

        # Assert
        assert isinstance(result, Router)
        assert result.name == "updated-name"
        persisted = (await db_session.execute(select(RouterTable).where(RouterTable.id == router.id))).scalar_one()
        assert persisted.name == "updated-name"

    async def test_update_router_should_return_router_with_updated_type(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router-type-update", type=RouterType.TEXT_GENERATION)
        await db_session.flush()

        # Act
        result = await repository.update_router(to_router_domain(router).with_type(RouterType.TEXT_EMBEDDINGS_INFERENCE))

        # Assert
        assert isinstance(result, Router)
        assert result.type == RouterType.TEXT_EMBEDDINGS_INFERENCE

    async def test_update_router_should_return_router_with_updated_costs(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router-costs-update", cost_prompt_tokens=0.001, cost_completion_tokens=0.002)
        await db_session.flush()

        # Act
        result = await repository.update_router(
            to_router_domain(router).with_cost_prompt_tokens(0.010).with_cost_completion_tokens(0.020).with_qos_retries_before_reject(3)
        )

        # Assert
        assert isinstance(result, Router)
        assert result.cost_prompt_tokens == 0.010
        assert result.cost_completion_tokens == 0.020
        assert result.qos_retries_before_reject == 3

    async def test_update_router_should_replace_aliases_in_database(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router-aliases-update", alias=["old-alias"])
        await db_session.flush()

        # Act
        await repository.update_router(to_router_domain(router, aliases=["old-alias"]).with_aliases(["new-alias-1", "new-alias-2"]))

        # Assert
        await db_session.flush()
        aliases = (await db_session.execute(select(RouterAliasTable.value).where(RouterAliasTable.router_id == router.id))).scalars().all()
        assert set(aliases) == {"new-alias-1", "new-alias-2"}

    async def test_update_router_should_delete_all_aliases_when_given_empty_list(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        router = RouterSQLFactory(user=user, name="router-aliases-clear", alias=["alias-to-remove"])
        await db_session.flush()

        # Act
        await repository.update_router(to_router_domain(router, aliases=["alias-to-remove"]).with_aliases([]))

        # Assert
        await db_session.flush()
        aliases = (await db_session.execute(select(RouterAliasTable).where(RouterAliasTable.router_id == router.id))).scalars().all()
        assert aliases == []

    async def test_update_router_should_return_router_name_already_exists_when_name_is_duplicate(self, repository, db_session):
        # Arrange
        user = UserSQLFactory()
        RouterSQLFactory(user=user, name="taken-name")
        router = RouterSQLFactory(user=user, name="router-to-rename")
        await db_session.flush()

        # Act
        result = await repository.update_router(to_router_domain(router).with_name("taken-name"))

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "taken-name"


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouterIdsByUserId:
    async def test_should_return_ids_of_routers_owned_by_user(self, repository, db_session):
        # Arrange
        user_a = UserSQLFactory()
        user_b = UserSQLFactory()

        router_1 = RouterSQLFactory(user=user_a, name="router_user_a_1")
        router_2 = RouterSQLFactory(user=user_a, name="router_user_a_2")
        RouterSQLFactory(user=user_b, name="router_user_b")
        await db_session.flush()

        # Act
        result = await repository.get_router_ids_by_user_id(user_id=user_a.id)

        # Assert
        assert sorted(result) == sorted([router_1.id, router_2.id])
