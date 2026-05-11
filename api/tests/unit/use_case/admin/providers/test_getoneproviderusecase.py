import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.provider.errors import ProviderNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import ProviderFactory, UserWithRoleFactory
from api.use_cases.admin.providers._getoneproviderusecase import GetOneProviderCommand, GetOneProviderUseCase, GetOneProviderUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository, user_with_role_query):
    return GetOneProviderUseCase(provider_repository=provider_repository, user_with_role_query=user_with_role_query)


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=42, user_id=1)


class TestGetOneProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_provider_when_user_is_admin_and_provider_exists(
        self, use_case, provider_repository, user_with_role_query, admin_user, sample_provider
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.provider_repository.get_one_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=admin_user.id, provider_id=42))

        # Assert
        assert isinstance(result, GetOneProviderUseCaseSuccess)
        assert result.provider == sample_provider
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)
        provider_repository.get_one_provider.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(self, use_case, provider_repository, admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.provider_repository.get_one_provider.return_value = None

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=admin_user.id, provider_id=99))

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.id == 99
        provider_repository.get_one_provider.assert_called_once_with(99)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, provider_repository, non_admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=non_admin_user.id, provider_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        provider_repository.get_one_provider.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=expired_user.id, provider_id=42))

        # Assert
        assert isinstance(result, UserExpiredError)
