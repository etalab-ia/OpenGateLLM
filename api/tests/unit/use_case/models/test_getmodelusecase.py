import datetime as dt
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.role.entities import Limit, LimitType
from api.domain.user.errors import UserExpiredError
from api.tests.unit.use_case.factories import RouterFactory, UserWithRoleFactory
from api.use_cases.models import GetModelCommand, GetModelUseCase, GetModelUseCaseSucess


@pytest.fixture
def router_repository():
    repo = Mock()
    repo.get_all_routers = AsyncMock()
    repo.get_organization_name = AsyncMock()
    return repo


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def use_case(router_repository, user_with_role_query):
    return GetModelUseCase(router_repository=router_repository, user_with_role_query=user_with_role_query)


@pytest.fixture
def default_command():
    return GetModelCommand(user_id=1, name="claude-3")


@pytest.fixture
def sample_routers():
    return [
        RouterFactory(
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
        ),
        RouterFactory(
            id=2,
            name="claude-3",
            type=RouterType.TEXT_GENERATION,
            aliases=["claude-3-opus"],
            user_id=101,
            created=int(datetime(2024, 1, 2).timestamp()),
            providers=1,
            max_context_length=200000,
            cost_prompt_tokens=0.015,
            cost_completion_tokens=0.075,
        ),
        RouterFactory(
            id=3,
            name="dall-e-3",
            type=RouterType.IMAGE_TEXT_TO_TEXT,
            aliases=[],
            user_id=100,
            created=int(datetime(2024, 1, 3).timestamp()),
            providers=0,
            max_context_length=0,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.0,
        ),
    ]


@pytest.fixture
def user_info_with_access():
    return UserWithRoleFactory(
        id=1,
        limits=[
            Limit(router_id=1, value=100, type=LimitType.RPM),
            Limit(router_id=2, value=None, type=LimitType.RPM),
        ],
    )


class TestGetModelUseCase:
    @pytest.mark.asyncio
    async def test_should_return_a_list_with_one_model_when_a_name_is_given(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        user_info_with_access,
        use_case,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_with_access
        router_repository.get_all_routers.return_value = sample_routers
        router_repository.get_organization_name.return_value = "Anthropic"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "claude-3"

    @pytest.mark.asyncio
    async def test_should_return_a_list_with_one_model_when_an_alias_is_given(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        user_info_with_access,
        use_case,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_with_access
        router_repository.get_all_routers.return_value = sample_routers
        router_repository.get_organization_name.return_value = "OpenAI"
        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "claude-3"
        assert "claude-3-opus" in result.model.aliases

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_given_a_name_that_does_not_exist(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        user_info_with_access,
        use_case,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_with_access
        router_repository.get_all_routers.return_value = sample_routers
        command = GetModelCommand(user_id=1, name="non-existent-model")

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "non-existent-model"

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_given_a_name_and_no_limit_no_admin_permission(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        use_case,
        default_command,
    ):
        # Arrange
        user_info_no_access = UserWithRoleFactory(id=2, limits=[], permissions=[])
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_no_access
        router_repository.get_all_routers.return_value = sample_routers

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "claude-3"

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_when_limit_is_zero(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        use_case,
        default_command,
    ):
        # Arrange
        user_info_zero_limit = UserWithRoleFactory(id=1, limits=[Limit(router_id=2, value=0, type=LimitType.RPM)], permissions=[])
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_zero_limit
        router_repository.get_all_routers.return_value = sample_routers
        router_repository.get_organization_name.return_value = "Anthropic"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, ModelNotFoundError)
        assert result.name == "claude-3"

    @pytest.mark.asyncio
    async def test_should_return_the_router_when_associated_limit_value_is_none(
        self,
        router_repository,
        user_with_role_query,
        sample_routers,
        use_case,
        default_command,
    ):
        # Arrange
        user_info_unlimited = UserWithRoleFactory(id=1, limits=[Limit(router_id=2, value=None, type=LimitType.RPM)], permissions=[])
        user_with_role_query.get_user_with_role_by_id.return_value = user_info_unlimited
        router_repository.get_all_routers.return_value = sample_routers
        router_repository.get_organization_name.return_value = "Anthropic"

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetModelUseCaseSucess)
        assert result.model.id == "claude-3"

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, user_with_role_query, expired_user, use_case, default_command):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
