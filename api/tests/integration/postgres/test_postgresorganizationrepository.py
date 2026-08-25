import pytest
from sqlalchemy import select

from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationHasUsersError, OrganizationNotFoundError
from api.infrastructure.postgres import PostgresOrganizationRepository
from api.sql.models import Organization as OrganizationTable
from api.tests.integration.factories.sql import OrganizationSQLFactory, UserSQLFactory


@pytest.fixture
def repository(db_session):
    return PostgresOrganizationRepository(postgres_session=db_session)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateOrganization:
    async def test_create_organization_should_return_created_organization(self, repository, db_session):
        # Act
        result = await repository.create_organization(name="Acme Corp")

        # Assert
        assert isinstance(result, Organization)
        assert result.name == "Acme Corp"
        assert result.users == 0
        assert isinstance(result.id, int)
        assert result.created is not None
        assert result.updated is not None

        stored = await db_session.scalar(select(OrganizationTable).where(OrganizationTable.id == result.id))
        assert stored is not None
        assert stored.name == "Acme Corp"

    async def test_create_organization_should_return_already_exists_error_when_name_is_duplicate(self, repository, db_session):
        # Arrange
        OrganizationSQLFactory(name="Duplicate Org")
        await db_session.flush()

        # Act
        result = await repository.create_organization(name="Duplicate Org")

        # Assert
        assert isinstance(result, OrganizationAlreadyExistsError)
        assert result.name == "Duplicate Org"


@pytest.mark.asyncio(loop_scope="session")
class TestGetOrganizationByName:
    async def test_get_organization_by_name_should_return_organization_when_it_exists(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Existing Org")
        await db_session.flush()

        # Act
        result = await repository.get_organization_by_name(name="Existing Org")

        # Assert
        assert isinstance(result, Organization)
        assert result.id == organization.id
        assert result.name == "Existing Org"
        assert result.users == 0
        assert result.created == organization.created
        assert result.updated == organization.updated

    async def test_get_organization_by_name_should_return_user_count(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org With Users")
        UserSQLFactory(organization=organization)
        UserSQLFactory(organization=organization)
        await db_session.flush()

        # Act
        result = await repository.get_organization_by_name(name="Org With Users")

        # Assert
        assert isinstance(result, Organization)
        assert result.id == organization.id
        assert result.name == "Org With Users"
        assert result.users == 2

    async def test_get_organization_by_name_should_return_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_organization_by_name(name="Missing Org")

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.name == "Missing Org"


@pytest.mark.asyncio(loop_scope="session")
class TestGetOrganizationById:
    async def test_get_organization_by_id_should_return_organization_with_user_count(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org By Id")
        UserSQLFactory(organization=organization)
        await db_session.flush()

        # Act
        result = await repository.get_organization_by_id(organization_id=organization.id)

        # Assert
        assert isinstance(result, Organization)
        assert result.id == organization.id
        assert result.name == "Org By Id"
        assert result.users == 1

    async def test_get_organization_by_id_should_return_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.get_organization_by_id(organization_id=999999)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 999999


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteOrganization:
    async def test_delete_organization_should_return_deleted_organization(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org To Delete")
        await db_session.flush()

        # Act
        result = await repository.delete_organization(organization_id=organization.id)

        # Assert
        assert isinstance(result, Organization)
        assert result.id == organization.id
        assert result.name == "Org To Delete"

        stored = await db_session.scalar(select(OrganizationTable).where(OrganizationTable.id == organization.id))
        assert stored is None

    async def test_delete_organization_should_return_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Act
        result = await repository.delete_organization(organization_id=999999)

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 999999

    async def test_delete_organization_should_return_has_users_error_when_organization_still_has_users(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org With Users To Delete")
        UserSQLFactory(organization=organization)
        UserSQLFactory(organization=organization)
        await db_session.flush()

        # Act
        result = await repository.delete_organization(organization_id=organization.id)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == organization.id
        assert result.number_of_users == 2

        stored = await db_session.scalar(select(OrganizationTable).where(OrganizationTable.id == organization.id))
        assert stored is not None
