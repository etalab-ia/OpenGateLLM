import pytest
from sqlalchemy import select

from api.domain.role.entities import PermissionType
from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.sql.models import Permission, User
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory
from api.use_cases.admin.bootstrapadminusecase import BootstrapAdminUseCase
from api.utils.lifespan import bootstrap_admin_role_and_user

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "s3cr3t"


@pytest.fixture
def bootstrap_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(
            auth_bootsrap_admin_username=ADMIN_USERNAME,
            auth_bootsrap_admin_password=ADMIN_PASSWORD,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )


@pytest.mark.asyncio(loop_scope="session")
class TestBootstrapAdmin:
    async def test_creates_admin_user_and_role_when_no_admin_exists(self, db_session, bootstrap_configuration):
        # Act
        await bootstrap_admin_role_and_user(configuration=bootstrap_configuration, postgres_session=db_session)
        await db_session.flush()

        # Assert
        user = (await db_session.execute(select(User).where(User.email == ADMIN_USERNAME))).scalar_one_or_none()
        assert user is not None
        assert user.email == ADMIN_USERNAME

        permission = (
            await db_session.execute(select(Permission).where(Permission.role_id == user.role_id, Permission.permission == PermissionType.ADMIN))
        ).scalar_one_or_none()
        assert permission is not None

    async def test_skips_when_admin_user_already_exists(self, db_session, bootstrap_configuration):
        # Arrange
        UserSQLFactory(admin_user=True)
        await db_session.flush()

        # Act
        await bootstrap_admin_role_and_user(configuration=bootstrap_configuration, postgres_session=db_session)

    async def test_reuses_existing_role_and_adds_admin_permission_when_role_name_already_taken(self, db_session, bootstrap_configuration):
        # Arrange
        role = RoleSQLFactory(name=BootstrapAdminUseCase.BOOTSTRAP_ADMIN_ROLE_NAME)
        await db_session.flush()

        # Act
        await bootstrap_admin_role_and_user(configuration=bootstrap_configuration, postgres_session=db_session)

        # Assert
        user = (await db_session.execute(select(User).where(User.email == ADMIN_USERNAME))).scalar_one_or_none()
        assert user is not None
        assert user.role_id == role.id

        permission = (
            await db_session.execute(select(Permission).where(Permission.role_id == role.id, Permission.permission == PermissionType.ADMIN))
        ).scalar_one_or_none()
        assert permission is not None

    async def test_updates_existing_user_when_user_email_already_taken(self, db_session, bootstrap_configuration):
        # Arrange
        user = UserSQLFactory(regular_user=True, email=ADMIN_USERNAME)
        await db_session.flush()

        # Act
        await bootstrap_admin_role_and_user(configuration=bootstrap_configuration, postgres_session=db_session)

        # Assert
        updated_user = (await db_session.execute(select(User).where(User.id == user.id))).scalar_one()
        assert updated_user.id == user.id

        permission = (
            await db_session.execute(
                select(Permission).where(Permission.role_id == updated_user.role_id, Permission.permission == PermissionType.ADMIN)
            )
        ).scalar_one_or_none()
        assert permission is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
