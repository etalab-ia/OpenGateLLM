from unittest.mock import AsyncMock

import pytest

from api.domain.provider.errors import ProviderNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import ProviderFactory, UserInfoFactory
from api.use_cases.admin.providers._getoneproviderusecase import GetOneProviderCommand, GetOneProviderUseCase, GetOneProviderUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository, user_info_repository):
    return GetOneProviderUseCase(provider_repository=provider_repository, user_info_repository=user_info_repository)


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=42, user_id=1)


class TestGetOneProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_provider_when_user_is_admin_and_provider_exists(
        self, use_case, provider_repository, user_info_repository, admin_user_info, sample_provider
    ):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.provider_repository.get_one_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=admin_user_info.id, provider_id=42))

        # Assert
        assert isinstance(result, GetOneProviderUseCaseSuccess)
        assert result.provider == sample_provider
        user_info_repository.get_user_info.assert_called_once_with(user_id=admin_user_info.id)
        provider_repository.get_one_provider.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(self, use_case, provider_repository, admin_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.provider_repository.get_one_provider.return_value = None

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=admin_user_info.id, provider_id=99))

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.provider_id == 99
        provider_repository.get_one_provider.assert_called_once_with(99)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(self, use_case, provider_repository, unauthorized_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(user_id=unauthorized_user_info.id, provider_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        provider_repository.get_one_provider.assert_not_called()
