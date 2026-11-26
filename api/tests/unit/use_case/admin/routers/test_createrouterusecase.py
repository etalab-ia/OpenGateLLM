from unittest.mock import create_autospec

import pytest

from api.domain.router import RouterAuthorization, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, UserCannotCreateRouterError
from api.tests.unit.use_case.factories import RouterFactory
from api.use_cases.admin.routers import CreateRouterCommand, CreateRouterUseCase, CreateRouterUseCaseSuccess


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_router_authorization():
    authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
    authorization.can_create_router.return_value = True
    return authorization


@pytest.fixture
def use_case(mock_router_repository, mock_router_authorization):
    return CreateRouterUseCase(router_repository=mock_router_repository, router_authorization=mock_router_authorization)


@pytest.fixture
def sample_router_with_aliases():
    return RouterFactory(
        id=1,
        name="test-model",
        type=RouterType.TEXT_GENERATION,
        aliases=["alias1", "alias2"],
        user_id=1,
        qos_retries_before_reject=3,
        cost_prompt_tokens=0.01,
        cost_completion_tokens=0.02,
        providers=[],
    )


class TestCreateRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_create_router_with_aliases_when_aliases_are_given(
        self, use_case, mock_router_repository, mock_router_authorization, sample_router_with_aliases
    ):
        # Arrange
        mock_router_repository.create_router.return_value = sample_router_with_aliases

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.01,
                cost_completion_tokens=0.02,
                qos_retries_before_reject=3,
            )
        )

        # Assert
        assert isinstance(result, CreateRouterUseCaseSuccess)
        assert result.router == sample_router_with_aliases

        mock_router_authorization.can_create_router.assert_awaited_once_with(user_id=1)
        mock_router_repository.create_router.assert_awaited_once_with(
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=3,
            cost_prompt_tokens=0.01,
            cost_completion_tokens=0.02,
            user_id=1,
            aliases=["alias1", "alias2"],
        )

    @pytest.mark.asyncio
    async def test_should_create_router_without_aliases_if_no_alias_is_given(self, use_case, mock_router_repository, mock_router_authorization):
        # Arrange
        router_without_aliases = RouterFactory(
            id=2,
            name="model-no-alias",
            type=RouterType.TEXT_GENERATION,
            aliases=[],
            user_id=1,
        )

        mock_router_repository.create_router.return_value = router_without_aliases

        # Act
        result = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="model-no-alias",
                router_type=RouterType.TEXT_GENERATION,
                aliases=[],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert isinstance(result, CreateRouterUseCaseSuccess)
        assert result.router == router_without_aliases

        mock_router_authorization.can_create_router.assert_awaited_once_with(user_id=1)
        mock_router_repository.create_router.assert_awaited_once_with(
            name="model-no-alias",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=None,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            user_id=1,
            aliases=[],
        )

    @pytest.mark.asyncio
    async def test_should_return_an_error_without_creating_anything_when_the_user_is_not_allowed(
        self, use_case, mock_router_repository, mock_router_authorization
    ):
        # Arrange
        mock_router_authorization.can_create_router.return_value = False

        # Act
        error = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1"],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert error == UserCannotCreateRouterError(user_id=1)
        mock_router_repository.create_router.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_router_alias_already_exists_when_alias_already_exists(self, use_case, mock_router_repository):
        # Arrange
        mock_router_repository.create_router.return_value = RouterAliasAlreadyExistsError(aliases=["alias1"])

        # Act
        error = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert isinstance(error, RouterAliasAlreadyExistsError)
        mock_router_repository.create_router.assert_awaited_once_with(
            aliases=["alias1", "alias2"],
            cost_completion_tokens=0.0,
            cost_prompt_tokens=0.0,
            qos_retries_before_reject=None,
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            user_id=1,
        )

    @pytest.mark.asyncio
    async def test_should_return_router_name_already_exists_when_name_already_exists(self, use_case, mock_router_repository):
        # Arrange
        mock_router_repository.create_router.return_value = RouterNameAlreadyExistsError(name="existing-router")

        # Act
        error = await use_case.execute(
            command=CreateRouterCommand(
                user_id=1,
                name="test-model",
                router_type=RouterType.TEXT_GENERATION,
                aliases=["alias1", "alias2"],
                cost_prompt_tokens=0.0,
                cost_completion_tokens=0.0,
            )
        )

        # Assert
        assert isinstance(error, RouterNameAlreadyExistsError)
        mock_router_repository.create_router.assert_awaited_once_with(
            user_id=1,
            name="test-model",
            router_type=RouterType.TEXT_GENERATION,
            qos_retries_before_reject=None,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
            aliases=["alias1", "alias2"],
        )
