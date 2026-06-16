from unittest.mock import AsyncMock

import pytest

from api.domain.provider.errors import ProviderNotFoundError
from api.tests.unit.use_case.factories import ProviderFactory
from api.use_cases.admin.providers._getoneproviderusecase import GetOneProviderCommand, GetOneProviderUseCase, GetOneProviderUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository):
    return GetOneProviderUseCase(provider_repository=provider_repository)


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=42, user_id=1)


class TestGetOneProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_provider_when_user_is_admin_and_provider_exists(self, use_case, provider_repository, sample_provider):
        # Arrange

        use_case.provider_repository.get_one_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(provider_id=42))

        # Assert
        assert isinstance(result, GetOneProviderUseCaseSuccess)
        assert result.provider == sample_provider
        provider_repository.get_one_provider.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(self, use_case, provider_repository):
        # Arrange

        use_case.provider_repository.get_one_provider.return_value = None

        # Act
        result = await use_case.execute(command=GetOneProviderCommand(provider_id=99))

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.id == 99
        provider_repository.get_one_provider.assert_called_once_with(99)
