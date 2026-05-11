from datetime import UTC, datetime

import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import UserWithRoleView
from api.infrastructure.postgres import PostgresUserWithRoleQuery
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory


@pytest.fixture
def query(db_session):
    return PostgresUserWithRoleQuery(postgres_session=db_session)


def _to_epoch(value: datetime) -> int:
    return int(value.replace(tzinfo=UTC).timestamp())


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserWithRoleById:
    async def test_should_return_user_with_role_when_user_exists(self, query, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.ADMIN)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        user = UserSQLFactory(role=role, priority=5, budget=42.5)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.id == user.id
        assert result.email == user.email
        assert result.name == user.name
        assert result.organization == user.organization_id
        assert result.budget == 42.5
        assert result.priority == 5
        assert set(result.permissions) == {PermissionType.ADMIN, PermissionType.READ_METRIC}
        assert len(result.limits) == 1
        assert result.limits[0].router_id == router.id
        assert result.limits[0].type == LimitType.TPM
        assert result.limits[0].value == 100

    async def test_should_return_admin_true_when_user_has_admin_permission(self, query, db_session):
        # Arrange
        user = UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.is_admin is True

    async def test_should_return_admin_false_when_user_has_no_admin_permission(self, query, db_session):
        # Arrange
        user = UserSQLFactory(regular_user=True)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.is_admin is False

    async def test_should_return_empty_permissions_and_limits_when_role_has_none(self, query, db_session):
        # Arrange
        role = RoleSQLFactory()
        user = UserSQLFactory(role=role)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.permissions == []
        assert result.limits == []

    async def test_should_return_expiration_epoch_when_user_has_expires(self, query, db_session):
        # Arrange
        expires_at = datetime(2030, 1, 1, 12, 0, 0)
        user = UserSQLFactory(expires=expires_at)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.expires == _to_epoch(expires_at)

    async def test_should_return_none_expiration_when_user_never_expires(self, query, db_session):
        # Arrange
        user = UserSQLFactory(expires=None)
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.expires is None

    async def test_should_return_user_not_found_when_id_does_not_exist(self, query, db_session):
        # Act
        result = await query.get_user_with_role_by_id(user_id=999999)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999


@pytest.mark.asyncio(loop_scope="session")
class TestGetUserWithRoleByEmail:
    async def test_should_return_user_with_role_when_email_matches(self, query, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.PROVIDE_MODELS)
        user = UserSQLFactory(role=role, email="found@example.com")
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_email(email="found@example.com")

        # Assert
        assert isinstance(result, UserWithRoleView)
        assert result.id == user.id
        assert result.email == "found@example.com"
        assert result.permissions == [PermissionType.PROVIDE_MODELS]

    async def test_should_return_user_not_found_when_email_does_not_exist(self, query, db_session):
        # Act
        result = await query.get_user_with_role_by_email(email="missing@example.com")

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.email == "missing@example.com"

    async def test_should_match_email_exactly(self, query, db_session):
        # Arrange
        UserSQLFactory(email="exact@example.com")
        await db_session.flush()

        # Act
        result = await query.get_user_with_role_by_email(email="EXACT@example.com")

        # Assert
        assert isinstance(result, UserNotFoundError)
