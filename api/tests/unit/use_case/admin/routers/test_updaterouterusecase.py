from unittest.mock import create_autospec

import pytest

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError, UserCannotUpdateRouterError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import UpdateRouterCommand, UpdateRouterUseCase, UpdateRouterUseCaseSuccess


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_router_authorization():
    authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
    authorization.can_update_router.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_router_repository, mock_router_authorization):
    return UpdateRouterUseCase(router_repository=mock_router_repository, router_authorization=mock_router_authorization)


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1, name="original-name", aliases=[])


def full_command(router, **overrides) -> UpdateRouterCommand:
    """Command replacing every persisted field with the current router values, unless overridden."""
    command = UpdateRouterCommand(
        authenticated_user_id=7,
        router_id=router.id,
        name=router.name,
        router_type=router.type,
        aliases=router.aliases,
        cost_prompt_tokens=router.cost_prompt_tokens,
        cost_completion_tokens=router.cost_completion_tokens,
        qos_retries_before_reject=router.qos_retries_before_reject,
    )
    for field, value in overrides.items():
        setattr(command, field, value)
    return command


class TestUpdateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_updated_router_when_the_user_is_allowed_and_the_router_exists(
        self, use_case, mock_router_repository, mock_router_authorization, sample_router
    ):
        # Arrange
        updated_router = (
            sample_router.with_name("new-name")
            .with_type(RouterType.TEXT_EMBEDDINGS_INFERENCE)
            .with_cost_prompt_tokens(0.005)
            .with_cost_completion_tokens(0.010)
            .with_qos_retries_before_reject(2)
            .with_aliases(["alias-a", "alias-b"])
        )

        mock_router_repository.get_router_by_id.return_value = sample_router
        mock_router_repository.get_aliases.return_value = []
        mock_router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(
            command=full_command(
                sample_router,
                name="new-name",
                router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
                cost_prompt_tokens=0.005,
                cost_completion_tokens=0.010,
                qos_retries_before_reject=2,
                aliases=["alias-a", "alias-b"],
            )
        )

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        assert result.router == updated_router

        mock_router_authorization.can_update_router.assert_awaited_once_with(user_id=7, router_id=42)
        mock_router_repository.get_router_by_id.assert_awaited_once_with(router_id=42)
        mock_router_repository.update_router.assert_awaited_once_with(router=updated_router)

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_touching_the_repository_when_the_user_is_not_allowed(
        self, use_case, mock_router_repository, mock_router_authorization
    ):
        # Arrange
        mock_router_authorization.can_update_router.return_value = False

        # Act
        result = await use_case.execute(command=full_command(RouterFactory(id=42, user_id=1)))

        # Assert
        assert result == UserCannotUpdateRouterError(user_id=7)
        mock_router_authorization.can_update_router.assert_awaited_once_with(user_id=7, router_id=42)
        mock_router_repository.get_router_by_id.assert_not_awaited()
        mock_router_repository.get_aliases.assert_not_awaited()
        mock_router_repository.update_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, mock_router_repository):
        # Arrange

        mock_router_repository.get_router_by_id.return_value = RouterNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=full_command(RouterFactory(id=99, user_id=1)))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        mock_router_repository.update_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_alias_already_exists_error_when_alias_belongs_to_another_router(
        self, use_case, mock_router_repository, sample_router
    ):
        # Arrange

        mock_router_repository.get_router_by_id.return_value = sample_router
        mock_router_repository.get_aliases.return_value = ["conflicting-alias"]

        # Act
        result = await use_case.execute(command=full_command(sample_router, aliases=["conflicting-alias"]))

        # Assert
        assert isinstance(result, RouterAliasAlreadyExistsError)
        assert result.aliases == ["conflicting-alias"]
        mock_router_repository.update_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_not_flag_conflict_when_alias_already_belongs_to_the_same_router(self, use_case, mock_router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=["own-alias"])
        updated_router = router.with_aliases(["own-alias", "new-alias"])

        mock_router_repository.get_router_by_id.return_value = router
        mock_router_repository.get_aliases.return_value = ["own-alias"]
        mock_router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=["own-alias", "new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_router_repository.update_router.assert_awaited_once_with(router=router.with_aliases(["own-alias", "new-alias"]))

    @pytest.mark.asyncio
    async def test_should_clear_aliases_when_command_aliases_is_empty(self, use_case, mock_router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=["own-alias"])
        cleared_router = router.with_aliases([])

        mock_router_repository.get_router_by_id.return_value = router
        mock_router_repository.update_router.return_value = cleared_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=[]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        assert result.router == cleared_router
        mock_router_repository.get_aliases.assert_not_awaited()
        mock_router_repository.update_router.assert_awaited_once_with(router=cleared_router)

    @pytest.mark.asyncio
    async def test_should_propagate_router_name_already_exists_error_from_repository(self, use_case, mock_router_repository, sample_router):
        # Arrange

        mock_router_repository.get_router_by_id.return_value = sample_router
        mock_router_repository.update_router.return_value = RouterNameAlreadyExistsError(name="taken-name")

        # Act
        result = await use_case.execute(command=full_command(sample_router, name="taken-name"))

        # Assert
        assert isinstance(result, RouterNameAlreadyExistsError)
        assert result.name == "taken-name"

    @pytest.mark.asyncio
    async def test_should_add_aliases_when_router_has_no_aliases_and_command_updates_aliases(self, use_case, mock_router_repository):
        # Arrange
        router = RouterFactory(id=42, user_id=1, aliases=[])
        updated_router = router.with_aliases(["new-alias"])

        mock_router_repository.get_router_by_id.return_value = router
        mock_router_repository.get_aliases.return_value = []
        mock_router_repository.update_router.return_value = updated_router

        # Act
        result = await use_case.execute(command=full_command(router, aliases=["new-alias"]))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_router_repository.update_router.assert_awaited_once_with(router=router.with_aliases(["new-alias"]))

    @pytest.mark.asyncio
    async def test_should_not_call_update_router_when_router_should_not_be_updated(self, use_case, mock_router_repository, sample_router):
        # Arrange

        mock_router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=full_command(sample_router))

        # Assert
        assert isinstance(result, UpdateRouterUseCaseSuccess)
        mock_router_repository.update_router.assert_not_awaited()
