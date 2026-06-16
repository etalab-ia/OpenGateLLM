from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.role.entities import Limit, LimitType
from api.domain.router.errors import RouterNotFoundError
from api.tests.unit.use_case.factories import RouterFactory, UserWithRoleFactory
from api.use_cases.models import GetModelCommand, GetModelUseCase, GetModelUseCaseSucess


@pytest.fixture
def router_repository():
    repo = Mock()
    repo.get_router_by_name_or_alias = AsyncMock()
    repo.get_organization_name = AsyncMock()
    return repo


@pytest.fixture
def use_case(router_repository):
    return GetModelUseCase(router_repository=router_repository)


@pytest.fixture
def router():
    return RouterFactory(
        id=1,
        name="gpt-4",
        type=RouterType.TEXT_GENERATION,
        aliases=["gpt-4-turbo"],
        user_id=100,
        created=int(datetime(2024, 1, 1).timestamp()),
        providers=2,
        max_context_length=8192,
        cost_prompt_tokens=0.03,
        cost_completion_tokens=0.06,
    )


@pytest.fixture
def default_command():
    return GetModelCommand(user=UserWithRoleFactory(id=1, limits=[Limit(router_id=1, value=100, type=LimitType.RPM)]), name="gpt-4")


class TestGetModelUseCase:
    @pytest.mark.asyncio
    async def test_should_return_a_list_with_one_model_when_a_name_is_given(self, router_repository, router, use_case, default_command):
        # Arrange
        router_repository.get_router_by_name_or_alias.return_value = router
        router_repository.get_organization_name.return_value = "Anthropic"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "gpt-4"
        router_repository.get_router_by_name_or_alias.assert_awaited_once_with(name_or_alias="gpt-4")

    @pytest.mark.asyncio
    async def test_should_return_a_list_with_one_model_when_an_alias_is_given(self, router_repository, router, use_case, default_command):
        # Arrange
        router_repository.get_router_by_name_or_alias.return_value = router
        router_repository.get_organization_name.return_value = "OpenAI"
        default_command.name = "gpt-4-turbo"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "gpt-4"
        assert "gpt-4-turbo" in result.model.aliases
        router_repository.get_router_by_name_or_alias.assert_awaited_once_with(name_or_alias="gpt-4-turbo")

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_given_a_name_that_does_not_exist(self, router_repository, use_case, default_command):
        # Arrange
        router_repository.get_router_by_name_or_alias.return_value = RouterNotFoundError(name="non-existent-model")
        default_command.name = "non-existent-model"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "non-existent-model"

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_given_a_name_and_no_limit_no_admin_permission(
        self,
        router_repository,
        router,
        use_case,
        default_command,
    ):
        # Arrange
        default_command.user = UserWithRoleFactory(id=2, limits=[], permissions=[])

        router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "gpt-4"

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_when_limit_is_zero(
        self,
        router_repository,
        router,
        use_case,
        default_command,
    ):
        # Arrange
        default_command.user = UserWithRoleFactory(id=1, limits=[Limit(router_id=1, value=0, type=LimitType.RPM)], permissions=[])
        router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "gpt-4"

    @pytest.mark.asyncio
    async def test_should_return_the_router_when_associated_limit_value_is_none(
        self,
        router_repository,
        router,
        use_case,
        default_command,
    ):
        # Arrange
        default_command.user = UserWithRoleFactory(id=1, limits=[Limit(router_id=1, value=None, type=LimitType.RPM)], permissions=[])
        router_repository.get_router_by_name_or_alias.return_value = router
        router_repository.get_organization_name.return_value = "Anthropic"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "gpt-4"
