import pytest

from api.domain.role.entities import LimitType, PermissionType
from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.postgres import PostgresAuthenticatedUserQuery
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory


@pytest.fixture
def query(db_session):
    return PostgresAuthenticatedUserQuery(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestGetAuthenticatedUserById:
    async def test_should_return_user_when_user_exists(self, query, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.ADMIN)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        LimitSQLFactory(role=role, router=router, type=LimitType.RPM, value=10)

        user = UserSQLFactory(role=role, priority=5, budget=42.5)
        await db_session.flush()

        # Act
        result = await query.get_user_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, AuthenticatedUserView)
        assert result.id == user.id
        assert result.email == user.email
        assert result.name == user.name
        assert result.organization == user.organization_id
        assert result.budget == 42.5
        assert result.priority == 5
        assert set(result.permissions) == {PermissionType.ADMIN, PermissionType.READ_METRIC}
        assert len(result.limits) == 2
        assert result.limits[0].router_id == router.id
        assert result.limits[0].type == LimitType.TPM
        assert result.limits[0].value == 100
        assert result.limits[1].router_id == router.id
        assert result.limits[1].type == LimitType.RPM
        assert result.limits[1].value == 10

    async def test_should_return_admin_true_when_user_has_admin_permission(self, query, db_session):
        # Arrange
        user = UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        result = await query.get_user_by_id(user_id=user.id)

        # Assert
        assert isinstance(result, AuthenticatedUserView)
        assert result.is_admin is True

    async def test_should_return_user_not_found_when_id_does_not_exist(self, query, db_session):
        # Act
        result = await query.get_user_by_id(user_id=999999)

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.id == 999999


@pytest.mark.asyncio(loop_scope="session")
class TestGetAuthenticatedUserByEmail:
    async def test_should_return_user_when_email_matches(self, query, db_session):
        # Arrange
        role = RoleSQLFactory()
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        user = UserSQLFactory(role=role, email="found@example.com")
        await db_session.flush()

        # Act
        result = await query.get_user_by_email(email="found@example.com")

        # Assert
        assert isinstance(result, AuthenticatedUserView)
        assert result.id == user.id
        assert result.email == "found@example.com"
        assert result.permissions == [PermissionType.READ_METRIC]

    async def test_should_return_user_not_found_when_email_does_not_exist(self, query, db_session):
        # Act
        result = await query.get_user_by_email(email="missing@example.com")

        # Assert
        assert isinstance(result, UserNotFoundError)
        assert result.email == "missing@example.com"

    async def test_should_match_email_exactly(self, query, db_session):
        # Arrange
        UserSQLFactory(email="exact@example.com")
        await db_session.flush()

        # Act
        result = await query.get_user_by_email(email="EXACT@example.com")

        # Assert
        assert isinstance(result, UserNotFoundError)
