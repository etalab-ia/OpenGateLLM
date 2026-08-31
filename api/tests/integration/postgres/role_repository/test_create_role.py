import pytest

from api.domain.role.entities import Role
from api.domain.role.errors import RoleAlreadyExistsError
from api.infrastructure.postgres import PostgresRolesRepository


@pytest.fixture
def repository(db_session):
    return PostgresRolesRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRole:
    async def test_creates_role_and_returns_role_entity(self, repository, db_session):
        # Act
        result = await repository.create_role(name="test_role")

        # Assert
        assert isinstance(result, Role)
        assert result.name == "test_role"
        assert isinstance(result.id, int)

    async def test_returns_role_already_exists_error_when_name_is_duplicate(self, repository, db_session):
        # Arrange
        await repository.create_role(name="duplicate_role")

        # Act
        result = await repository.create_role(name="duplicate_role")

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert result.name == "duplicate_role"

    async def test_keeps_the_session_usable_when_name_is_duplicate(self, repository, db_session):
        """A caller losing a create race (concurrent bootstrap) must be able to read the role back on the same session."""
        # Arrange
        created = await repository.create_role(name="concurrent_role")

        # Act
        result = await repository.create_role(name="concurrent_role")
        role = await repository.get_role_with_permissions_and_limits_by_name(role_name="concurrent_role")

        # Assert
        assert isinstance(result, RoleAlreadyExistsError)
        assert isinstance(role, Role)
        assert role.id == created.id
