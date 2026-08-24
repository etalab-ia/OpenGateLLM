import pytest

from api.domain.role.entities import PermissionType
from api.domain.user.views import AuthenticatedUserView
from api.use_cases.me import GetMeCommand, GetMeUseCase, GetMeUseCaseSuccess


@pytest.fixture
def use_case():
    return GetMeUseCase()


@pytest.fixture
def authenticated_user():
    return AuthenticatedUserView(
        id=42,
        email="alice@example.com",
        name="Alice",
        organization_id=7,
        budget=10.0,
        permissions=[PermissionType.READ_METRIC],
        limits=[],
        expires=None,
    )


class TestGetMeUseCase:
    @pytest.mark.asyncio
    async def test_should_return_authenticated_user(self, use_case, authenticated_user):
        # Arrange
        command = GetMeCommand(authenticated_user=authenticated_user)

        # Act
        result = await use_case.execute(command)

        # Assert
        assert isinstance(result, GetMeUseCaseSuccess)
        assert result.authenticated_user is authenticated_user
