from unittest.mock import AsyncMock

import pytest

from api.domain.role.entities import PermissionType
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.unit.use_case.factories import RouterFactory, UserInfoFactory
from api.use_cases.admin.routers import GetOneRouterCommand, GetOneRouterUseCase, GetOneRouterUseCaseSuccess


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_info_repository():
    return AsyncMock()


@pytest.fixture
def use_case(router_repository, user_info_repository):
    return GetOneRouterUseCase(router_repository=router_repository, user_info_repository=user_info_repository)


@pytest.fixture
def admin_user_info():
    return UserInfoFactory(id=1, admin=True)


@pytest.fixture
def provider_user_info():
    return UserInfoFactory(id=2, permissions=[PermissionType.PROVIDE_MODELS], limits=[])


@pytest.fixture
def unauthorized_user_info():
    return UserInfoFactory(id=3, without_permission=True, limits=[])


@pytest.fixture
def sample_router():
    return RouterFactory(id=42, user_id=1)


class TestGetOneRouterUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_when_user_is_admin(self, use_case, router_repository, user_info_repository, admin_user_info, sample_router):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = sample_router

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=admin_user_info.id, router_id=42))

        # Assert
        assert isinstance(result, GetOneRouterUseCaseSuccess)
        assert result.router == sample_router
        user_info_repository.get_user_info.assert_called_once_with(user_id=admin_user_info.id)
        router_repository.get_router_by_id.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, router_repository, use_case, admin_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = admin_user_info
        use_case.router_repository.get_router_by_id.return_value = None

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=admin_user_info.id, router_id=99))

        # Assert
        assert isinstance(result, RouterNotFoundError)
        assert result.router_id == 99
        router_repository.get_router_by_id.assert_called_once_with(99)

    @pytest.mark.asyncio
    async def test_should_return_insufficient_permission_error_when_user_has_no_permission(self, router_repository, use_case, unauthorized_user_info):
        # Arrange
        use_case.user_info_repository.get_user_info.return_value = unauthorized_user_info

        # Act
        result = await use_case.execute(command=GetOneRouterCommand(user_id=unauthorized_user_info.id, router_id=42))

        # Assert
        assert isinstance(result, UserIsNotAdminError)
        router_repository.get_router_by_id.assert_not_called()
