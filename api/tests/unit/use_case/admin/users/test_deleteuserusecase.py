import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.user.errors import DeleteUserWithProvidersError, DeleteUserWithRoutersError, UserExpiredError, UserIsNotAdminError, UserNotFoundError
from api.tests.unit.use_case.factories import UserFactory, UserWithRoleFactory
from api.use_cases.admin.users import DeleteUserCommand, DeleteUserUseCase, DeleteUserUseCaseSuccess


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(user_repository, router_repository, provider_repository, user_with_role_query):
    return DeleteUserUseCase(
        user_repository=user_repository,
        router_repository=router_repository,
        provider_repository=provider_repository,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def non_admin_user():
    return UserWithRoleFactory(id=2, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=3, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def sample_user():
    return UserFactory(id=42)


class TestDeleteUserUseCase:
    @pytest.mark.asyncio
    async def test_should_return_deleted_user_when_admin_and_user_exists(
        self, use_case, user_repository, router_repository, provider_repository, user_with_role_query, admin_user, sample_user
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_ids_by_user_id.return_value = []
        provider_repository.get_provider_ids_by_user_id.return_value = []
        user_repository.delete_user.return_value = sample_user

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=admin_user.id, user_id=sample_user.id))

        # Assert
        assert isinstance(result, DeleteUserUseCaseSuccess)
        assert result.user == sample_user
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)
        user_repository.delete_user.assert_called_once_with(user_id=sample_user.id)

    @pytest.mark.asyncio
    async def test_should_return_user_not_found_error_when_user_does_not_exist(
        self, use_case, user_repository, router_repository, provider_repository, user_with_role_query, admin_user
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_ids_by_user_id.return_value = []
        provider_repository.get_provider_ids_by_user_id.return_value = []
        user_repository.delete_user.return_value = UserNotFoundError(id=99)

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=admin_user.id, user_id=99))

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 99
        user_repository.delete_user.assert_called_once_with(user_id=99)

    @pytest.mark.asyncio
    async def test_should_return_user_is_not_admin_error_when_user_is_not_admin(
        self, use_case, user_repository, user_with_role_query, non_admin_user
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=non_admin_user.id, user_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        user_repository.delete_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_is_expired(self, use_case, user_repository, user_with_role_query, expired_user):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=expired_user.id, user_id=42))

        # Assert
        assert isinstance(result, UserExpiredError)
        user_repository.delete_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_delete_user_with_routers_error_with_ids_when_user_has_routers(
        self, use_case, user_repository, router_repository, provider_repository, user_with_role_query, admin_user
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_ids_by_user_id.return_value = [1, 2, 3]

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=admin_user.id, user_id=42))

        # Assert
        assert isinstance(result, DeleteUserWithRoutersError)
        assert result.router_ids == [1, 2, 3]
        router_repository.get_router_ids_by_user_id.assert_called_once_with(user_id=42)
        provider_repository.get_provider_ids_by_user_id.assert_not_called()
        user_repository.delete_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_delete_user_with_providers_error_with_ids_when_user_has_providers(
        self, use_case, user_repository, router_repository, provider_repository, user_with_role_query, admin_user
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_ids_by_user_id.return_value = []
        provider_repository.get_provider_ids_by_user_id.return_value = [10, 20]

        # Act
        result = await use_case.execute(DeleteUserCommand(authenticated_user_id=admin_user.id, user_id=42))

        # Assert
        assert isinstance(result, DeleteUserWithProvidersError)
        assert result.provider_ids == [10, 20]
        provider_repository.get_provider_ids_by_user_id.assert_called_once_with(user_id=42)
        user_repository.delete_user.assert_not_called()
