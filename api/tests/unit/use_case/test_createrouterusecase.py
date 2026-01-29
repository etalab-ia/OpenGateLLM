from unittest.mock import AsyncMock

import pytest

from api.domain.router.entities import ModelType, RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.domain.userinfo.errors import InsufficientPermissionError
from api.tests.unit.use_case.factories import RouterFactory, UserInfoFactory
from api.use_cases.admin import (
    CreateRouterUseCase,
)


@pytest.fixture
def router_repository():
    repo = AsyncMock()
    return repo


@pytest.fixture
def user_info_repository():
    repo = AsyncMock()
    return repo


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user_info():
    return UserInfoFactory(id=2, without_permission=True, limits=[])


@pytest.fixture
def sample_router_with_aliases():
    return RouterFactory(
        id=1,
        name="test-model",
        type=ModelType.TEXT_GENERATION,
        aliases=["alias1", "alias2"],
        user_id=1,
        load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
        cost_prompt_tokens=0.01,
        cost_completion_tokens=0.02,
        providers=0,
    )


@pytest.fixture
def use_case(router_repository, user_info_repository):
    return CreateRouterUseCase(
        router_repository=router_repository,
        user_info_repository=user_info_repository,
    )


class TestCreateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_create_router_with_aliases_when_aliases_are_given(
        self, router_repository, user_info_repository, admin_user_info, sample_router_with_aliases, use_case
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        router_repository.create_router.return_value = sample_router_with_aliases

        # Act
        result = await use_case.execute(
            user_id=1,
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            aliases=["alias1", "alias2"],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.01,
            cost_completion_tokens=0.02,
        )

        # Assert
        assert result.router == sample_router_with_aliases

        user_info_repository.get_user_info.assert_called_once_with(user_id=1)
        router_repository.create_router.assert_called_once_with(
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.01,
            cost_completion_tokens=0.02,
            user_id=admin_user_info.id,
            aliases=["alias1", "alias2"],
        )

    @pytest.mark.asyncio
    async def test_should_create_router_without_aliases_if_no_alias_is_given(
        self, router_repository, user_info_repository, admin_user_info, use_case
    ):
        # Arrange
        router_without_aliases = RouterFactory(
            id=2,
            name="model-no-alias",
            type=ModelType.TEXT_GENERATION,
            aliases=[],
            user_id=1,
        )
        user_info_repository.get_user_info.return_value = admin_user_info
        router_repository.create_router.return_value = router_without_aliases

        # Act
        result = await use_case.execute(
            user_id=1,
            name="model-no-alias",
            router_type=ModelType.TEXT_GENERATION,
            aliases=[],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
        )

        # Assert
        assert result.router == router_without_aliases
        router_repository.create_router.assert_called_once_with(
            name="model-no-alias",
            router_type=ModelType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=admin_user_info.id,
            aliases=[],
        )

    @pytest.mark.asyncio
    async def test_should_return_insufficient_permission_error_if_user_not_admin(
        self, router_repository, user_info_repository, non_admin_user_info, use_case
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = non_admin_user_info

        # Act
        error = await use_case.execute(
            user_id=2,
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            aliases=[],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
        )

        # Assert
        assert isinstance(error, InsufficientPermissionError)
        router_repository.create_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_alias_already_exists_when_alias_already_exists(
        self, router_repository, user_info_repository, admin_user_info, use_case
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        router_repository.create_router.return_value = RouterAliasAlreadyExistsError(aliases=["alias1"])

        # Act
        error = await use_case.execute(
            user_id=1,
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            aliases=["alias1", "alias2"],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
        )

        # Assert
        assert isinstance(error, RouterAliasAlreadyExistsError)
        router_repository.create_router.assert_called_once_with(
            aliases=["alias1", "alias2"],
            cost_completion_tokens=0.0,
            cost_prompt_tokens=0.0,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            user_id=1,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_name_already_exists_when_name_already_exists(
        self, router_repository, user_info_repository, admin_user_info, use_case
    ):
        # Arrange
        user_info_repository.get_user_info.return_value = admin_user_info
        router_repository.create_router.return_value = RouterNameAlreadyExistsError(name="existing-router")

        # Act
        error = await use_case.execute(
            user_id=1,
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            aliases=["alias1", "alias2"],
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
        )

        # Assert
        assert isinstance(error, RouterNameAlreadyExistsError)
        router_repository.create_router.assert_called_once_with(
            name="test-model",
            router_type=ModelType.TEXT_GENERATION,
            load_balancing_strategy=RouterLoadBalancingStrategy.SHUFFLE,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=admin_user_info.id,
            aliases=["alias1", "alias2"],
        )
