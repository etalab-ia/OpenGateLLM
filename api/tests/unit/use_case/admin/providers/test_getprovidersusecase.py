import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain import SortOrder
from api.domain.provider.entities import ProviderPage, ProviderSortField
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
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
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def sample_providers():
    return [ProviderFactory(id=1, user_id=1), ProviderFactory(id=2, user_id=1)]


@pytest.fixture
def default_command():
    return GetProvidersCommand(user_id=1, router_id=None, offset=0, limit=10, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC)


class TestGetProvidersUseCase:
    @pytest.mark.asyncio
    async def test_should_return_providers_when_user_is_admin(
        self, use_case, provider_repository, user_with_role_query, admin_user, sample_providers, default_command
    ):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.provider_repository.get_providers_page.return_value = ProviderPage(total=2, data=sample_providers)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetProvidersUseCaseSuccess)
        assert result.page.data == sample_providers
        assert result.page.total == 2
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_an_admin(self, use_case, provider_repository, non_admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(
            command=GetProvidersCommand(
                user_id=non_admin_user.id, router_id=None, offset=0, limit=10, sort_by=ProviderSortField.ID, sort_order=SortOrder.ASC
            )
        )

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        provider_repository.get_providers_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_forward_pagination_params_to_repository(self, use_case, provider_repository, admin_user, sample_providers):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
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

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user, default_command):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
