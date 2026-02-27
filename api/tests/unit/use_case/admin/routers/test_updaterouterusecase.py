from unittest.mock import AsyncMock

import pytest

from api.domain.model import ModelType as RouterType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RouterFactory, UserInfoFactory
from api.use_cases.admin.routers._updaterouterusecase import UpdateRouterCommand, UpdateRouterUseCase, UpdateRouterUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, user_info_repository):
    return UpdateRouterUseCase(router_repository=router_repository, user_info_repository=user_info_repository)


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1, name="original-name", aliases=[])


class TestUpdateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_router_when_user_is_admin_and_router_exists(
        self, use_case, router_repository, user_info_repository, admin_user_info, sample_router
    ):
        # Arrange
        updated_router = (
            sample_router.with_name("new-name")
            .with_type(RouterType.TEXT_EMBEDDINGS_INFERENCE)
            .with_load_balancing_strategy(RouterLoadBalancingStrategy.LEAST_BUSY)
            .with_cost_prompt_tokens(0.005)
            .with_cost_completion_tokens(0.010)
            .with_aliases(["alias-a", "alias-b"])
        )
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.get_aliases.return_value = []
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(
            command=UpdateRouterCommand(
                user_id=admin_user_info.id,
                router_id=42,
                name="new-name",
                router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
                load_balancing_strategy=RouterLoadBalancingStrategy.LEAST_BUSY,
                cost_prompt_tokens=0.005,
                cost_completion_tokens=0.010,
                aliases=["alias-a", "alias-b"],
            )
        )

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        assert result.router == updated_router
        user_info_repository.get_user_info.assert_called_once_with(user_id=admin_user_info.id)
        router_repository.get_router_by_id.assert_called_once_with(router_id=42)
        router_repository.update_router.assert_called_once_with(router_to_update=updated_router)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, router_repository, unauthorized_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=unauthorized_user_info.id, router_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        router_repository.get_router_by_id.assert_not_called()
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, router_repository, admin_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.router_id == 99
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_alias_already_exists_error_when_alias_belongs_to_another_router(
        self, use_case, router_repository, admin_user_info, sample_router
    ):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.get_aliases.return_value = ["conflicting-alias"]

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42, aliases=["conflicting-alias"]))

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["conflicting-alias"]
        router_repository.update_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_flag_conflict_when_alias_already_belongs_to_the_same_router(self, use_case, router_repository, admin_user_info):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=["own-alias"])
        updated_router = router.with_aliases(["own-alias", "new-alias"])
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = router
        use_case.router_repository.get_aliases.return_value = ["own-alias"]
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42, aliases=["own-alias", "new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_called_once_with(router_to_update=router.with_aliases(["own-alias", "new-alias"]))

    @pytest.mark.asyncio
    async def test_should_not_check_aliases_when_command_aliases_is_none(self, use_case, router_repository, admin_user_info, sample_router):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.update_router.return_value = sample_router

        # Act
        await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42, aliases=None))

        # Assert
        router_repository.get_aliases.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_propagate_router_name_already_exists_error_from_repository(
        self, use_case, router_repository, admin_user_info, sample_router
    ):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router
        use_case.router_repository.update_router.return_value = RouterNameAlreadyExistsError(name="taken-name")

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42, name="taken-name"))

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "taken-name"

    @pytest.mark.asyncio
    async def test_should_add_aliases_when_router_has_no_aliases_and_command_updates_aliases(self, use_case, router_repository, admin_user_info):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=None)
        updated_router = router.with_aliases(["new-alias"])
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = router
        use_case.router_repository.get_aliases.return_value = []
        use_case.router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42, aliases=["new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_called_once_with(router_to_update=router.with_aliases(["new-alias"]))

    @pytest.mark.asyncio
    async def test_should_not_call_update_router_when_router_should_not_be_updated(self, use_case, router_repository, admin_user_info, sample_router):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=UpdateRouterCommand(user_id=admin_user_info.id, router_id=42))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        router_repository.update_router.assert_not_called()
