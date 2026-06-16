from unittest.mock import AsyncMock

import pytest

from api.domain import SortOrder
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.tests.unit.use_case.factories import ProviderFactory
from api.use_cases.admin.providers import GetProvidersCommand, GetProvidersUseCase, GetProvidersUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository):
    return GetProvidersUseCase(provider_repository=provider_repository)


@pytest.fixture
def sample_providers():
    return [ProviderFactory(id=1, user_id=1), ProviderFactory(id=2, user_id=1)]


@pytest.fixture
def default_command():
    return GetProvidersCommand(router_id=None, offset=0, limit=10, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC)


class TestGetProvidersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_providers_when_user_is_admin(self, use_case, provider_repository, sample_providers, default_command):
        # Arrange

        use_case.provider_repository.get_providers_page.return_value = ProviderPage(total=2, data=sample_providers)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetProvidersUseCaseSuccess)
        assert result.page.data == sample_providers
        assert result.page.total == 2

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, provider_repository, sample_providers):
        # Arrange

        use_case.provider_repository.get_providers_page.return_value = ProviderPage(total=2, data=sample_providers)
        command = GetProvidersCommand(router_id=42, offset=5, limit=20, sort_by=ProviderSortField.MODEL_NAME, sort_order=SortOrder.DESC)

        # Act
        await use_case.execute(command=command)

        # Assert
        provider_repository.get_providers_page.assert_called_once_with(
            router_id=42,
            limit=20,
            offset=5,
            sort_by=ProviderSortField.MODEL_NAME,
            sort_order=SortOrder.DESC,
        )
