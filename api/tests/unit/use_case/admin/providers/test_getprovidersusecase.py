from unittest.mock import AsyncMock

import pytest

from api.domain import SortOrder
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.domain.user.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import ProviderFactory, UserWithRoleFactory
from api.use_cases.admin.providers import GetProvidersCommand, GetProvidersUseCase, GetProvidersUseCaseSuccess


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(provider_repository, user_with_role_query):
    return GetProvidersUseCase(provider_repository=provider_repository, user_with_role_query=user_with_role_query)


@pytest.fixture
def admin_user_info():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def unauthorized_user_info():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_providers():
    return [ProviderFactory(id=1, user_id=1), ProviderFactory(id=2, user_id=1)]


@pytest.fixture
def sample_command():
    return GetProvidersCommand(user_id=1, router_id=None, offset=0, limit=10, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC)


class TestGetProvidersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_providers_when_user_is_admin(
        self, use_case, provider_repository, user_with_role_query, admin_user_info, sample_providers, sample_command
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user_info
        use_case.provider_repository.get_providers_page.return_value = ProviderPage(total=2, data=sample_providers)

        # Act
        result = await use_case.execute(command=sample_command)

        # Assert
        assert isinstance(result, GetProvidersUseCaseSuccess)
        assert result.page.data == sample_providers
        assert result.page.total == 2
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user_info.id)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_an_admin(self, use_case, provider_repository, unauthorized_user_info):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(
            command=GetProvidersCommand(
                user_id=unauthorized_user_info.id, router_id=None, offset=0, limit=10, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC
            )
        )

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        provider_repository.get_providers_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, provider_repository, admin_user_info, sample_providers):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user_info
        use_case.provider_repository.get_providers_page.return_value = ProviderPage(total=2, data=sample_providers)
        command = GetProvidersCommand(user_id=1, router_id=42, offset=5, limit=20, sort_by=ProviderSortField.MODEL_NAME, sort_order=SortOrder.DESC)

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
