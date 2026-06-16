from unittest.mock import AsyncMock

import pytest

from api.domain.provider.errors import ProviderNotFoundError
from api.tests.unit.use_case.factories import ProviderFactory
from api.use_cases.admin.providers._deleteproviderusecase import DeleteProviderCommand, DeleteProviderUseCase, DeleteProviderUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository):
    return DeleteProviderUseCase(provider_repository=provider_repository)


@pytest.fixture
def sample_provider():
    return ProviderFactory(id=42, user_id=1)


class TestDeleteProviderUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_provider_when_user_is_admin_and_provider_exists(self, use_case, provider_repository, sample_provider):
        # Arrange

        use_case.provider_repository.delete_provider.return_value = sample_provider

        # Act
        result = await use_case.execute(command=DeleteProviderCommand(provider_id=42))

        # Assert
        assert isinstance(result, DeleteProviderUseCaseSuccess)
        assert result.deleted_provider == sample_provider
        provider_repository.delete_provider.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_found_error_when_provider_does_not_exist(self, use_case, provider_repository):
        # Arrange

        use_case.provider_repository.delete_provider.return_value = ProviderNotFoundError(id=99)

        # Act
        result = await use_case.execute(command=DeleteProviderCommand(provider_id=99))

        # Assert
        assert isinstance(result, ProviderNotFoundError)
        assert result.id == 99
        provider_repository.delete_provider.assert_called_once_with(99)
