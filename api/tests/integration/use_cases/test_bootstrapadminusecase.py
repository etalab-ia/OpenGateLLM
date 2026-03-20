import pytest
import pytest_asyncio
from sqlalchemy import func, select

from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user.errors import UserAlreadyExistsError
from api.infrastructure.postgres import PostgresRolesRepository, PostgresUserRepository
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable
from api.tests.integration.factories import RoleSQLFactory, UserSQLFactory
from api.use_cases.admin.bootstrapadminusecase import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    BootstrapAdminUseCaseSkipped,
    BootstrapAdminUseCaseSuccess,
)


@pytest.mark.asyncio(loop_scope="session")
class TestBootstrapAdminUseCase:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.use_case = BootstrapAdminUseCase(
            user_repository=PostgresUserRepository(postgres_session=db_session),
            role_repository=PostgresRolesRepository(postgres_session=db_session),
        )
        self.command = BootstrapAdminCommand(
            name="admin",
            email="admin@opengatellm.org",
            password="s3cr3t",
            permissions=[PermissionType.ADMIN],
            limits=[],
        )

    async def test_happy_path_returns_success_instance(self, db_session):
        result = await self.use_case.execute(self.command)

        assert isinstance(result, BootstrapAdminUseCaseSuccess)

    async def test_happy_path_result_contains_correct_email_and_ids(self, db_session):
        result = await self.use_case.execute(self.command)

        assert result.email == "admin@opengatellm.org"
        assert isinstance(result.user_id, int)
        assert isinstance(result.role_id, int)

    async def test_happy_path_admin_has_admin_permission_in_db(self, db_session):
        await self.use_case.execute(self.command)
        await db_session.flush()

        assert await self.use_case.user_repository.has_admin_user() is True

    async def test_skips_when_admin_user_already_exists(self, db_session):
        UserSQLFactory(admin_user=True)
        await db_session.flush()

        result = await self.use_case.execute(self.command)

        assert isinstance(result, BootstrapAdminUseCaseSkipped)

    async def test_skip_does_not_create_additional_roles_or_users(self, db_session):
        UserSQLFactory(admin_user=True)
        await db_session.flush()

        role_count_before = (await db_session.execute(select(func.count()).select_from(RoleTable))).scalar()
        user_count_before = (await db_session.execute(select(func.count()).select_from(UserTable))).scalar()

        await self.use_case.execute(self.command)
        await db_session.flush()

        role_count_after = (await db_session.execute(select(func.count()).select_from(RoleTable))).scalar()
        user_count_after = (await db_session.execute(select(func.count()).select_from(UserTable))).scalar()

        assert role_count_after == role_count_before
        assert user_count_after == user_count_before

    async def test_returns_role_already_exists_error_when_role_name_conflicts(self, db_session):
        RoleSQLFactory(name="admin")
        await db_session.flush()

        result = await self.use_case.execute(self.command)

        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "admin"

    async def test_returns_user_already_exists_error_when_email_conflicts(self, db_session):
        UserSQLFactory(email="admin@opengatellm.org", regular_user=True)
        await db_session.flush()

        command = BootstrapAdminCommand(
            name="admin",
            email="admin@opengatellm.org",
            password="s3cr3t",
            permissions=[PermissionType.ADMIN],
            limits=[],
        )
        result = await self.use_case.execute(command)

        assert isinstance(result, UserAlreadyExistsError)
        assert result.email == "admin@opengatellm.org"


@pytest.mark.asyncio(loop_scope="session")
class TestBootstrapAdminUseCaseUsernameCustomization:
    """Verify that auth_default_username from configuration is respected."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.use_case = BootstrapAdminUseCase(
            user_repository=PostgresUserRepository(postgres_session=db_session),
            role_repository=PostgresRolesRepository(postgres_session=db_session),
        )

    async def test_custom_username_is_used_as_email(self, db_session):
        """Simulates auth_default_username="superadmin" from config."""
        command = BootstrapAdminCommand(
            name="superadmin",
            email="superadmin",
            password="s3cr3t",
            permissions=[PermissionType.ADMIN],
            limits=[],
        )
        result = await self.use_case.execute(command)

        assert isinstance(result, BootstrapAdminUseCaseSuccess)
        assert result.email == "superadmin"

    async def test_custom_password_is_accepted(self, db_session):
        """Simulates auth_default_password="my-strong-pass" from config."""
        command = BootstrapAdminCommand(
            name="customadmin",
            email="customadmin",
            password="my-strong-pass",
            permissions=[PermissionType.ADMIN],
            limits=[],
        )
        result = await self.use_case.execute(command)

        assert isinstance(result, BootstrapAdminUseCaseSuccess)
