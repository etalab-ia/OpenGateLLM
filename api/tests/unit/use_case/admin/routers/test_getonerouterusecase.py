import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.router.errors import RouterNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.unit.use_case.factories import RouterFactory, UserWithRoleFactory
from api.use_cases.admin.routers import GetOneRouterCommand, GetOneRouterUseCase, GetOneRouterUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, user_with_role_query):
    return GetOneRouterUseCase(router_repository=router_repository, user_with_role_query=user_with_role_query)


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
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestGetOneRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_when_user_is_admin(self, use_case, router_repository, user_with_role_query, admin_user, sample_router):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=admin_user.id, router_id=42))

        # Assert
        assert isinstance(result, GetOneRouterUseCaseSuccess)
        assert result.router == sample_router
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=admin_user.id)
        router_repository.get_router_by_id.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, router_repository, use_case, admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        use_case.router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=admin_user.id, router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.id == 99
        router_repository.get_router_by_id.assert_called_once_with(99)

    @pytest.mark.asyncio
    async def test_should_return_insufficient_permission_error_when_user_has_no_permission(self, router_repository, use_case, non_admin_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = non_admin_user

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=non_admin_user.id, router_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        router_repository.get_router_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(self, use_case, expired_user):
        # Arrange
        use_case.user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=expired_user.id, router_id=42))

        # Assert
        assert isinstance(result, UserExpiredError)
