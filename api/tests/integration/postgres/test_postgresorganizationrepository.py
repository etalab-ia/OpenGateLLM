from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from api.domain import SortOrder
from api.domain.organization.entities import Organization, OrganizationSortField
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
class TestGetOrganizationsPage:
    async def test_returns_organizations_with_user_count(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org Page With Users")
        UserSQLFactory(organization=organization)
        UserSQLFactory(organization=organization)
        await db_session.flush()

        # Act
        result = await repository.get_organizations_page(limit=100, offset=0)

        # Assert
        listed = {organization.id: organization for organization in result.data}
        assert listed[organization.id].name == "Org Page With Users"
        assert listed[organization.id].users == 2

    async def test_returns_total_independent_of_limit(self, repository, db_session):
        # Arrange
        OrganizationSQLFactory(name="Org Page Total 1")
        OrganizationSQLFactory(name="Org Page Total 2")
        OrganizationSQLFactory(name="Org Page Total 3")
        await db_session.flush()
        stored = await db_session.scalar(select(func.count()).select_from(OrganizationTable))

        # Act
        result = await repository.get_organizations_page(limit=2, offset=0)

        # Assert
        assert len(result.data) == 2
        assert result.total == stored

    async def test_returns_empty_page_with_total_when_offset_is_out_of_range(self, repository, db_session):
        # Arrange
        OrganizationSQLFactory(name="Org Page Out Of Range")
        await db_session.flush()
        stored = await db_session.scalar(select(func.count()).select_from(OrganizationTable))

        # Act
        result = await repository.get_organizations_page(limit=10, offset=stored)

        # Assert
        assert result.data == []
        assert result.total == stored

    async def test_returns_organizations_sorted_by_name_descending(self, repository, db_session):
        # Arrange
        OrganizationSQLFactory(name="Org Page Sort A")
        OrganizationSQLFactory(name="Org Page Sort B")
        OrganizationSQLFactory(name="Org Page Sort C")
        await db_session.flush()

        # Act
        result = await repository.get_organizations_page(limit=100, offset=0, sort_by=OrganizationSortField.NAME, sort_order=SortOrder.DESC)

        # Assert
        names = [organization.name for organization in result.data]
        assert names == sorted(names, reverse=True)


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
        assert result.users == 0

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
        await db_session.flush()

        # Act
        result = await repository.delete_organization(organization_id=organization.id)

        # Assert
        assert isinstance(result, OrganizationHasUsersError)
        assert result.id == organization.id


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateOrganization:
    async def test_update_organization_should_return_renamed_organization(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org To Rename", updated=datetime(2020, 1, 1, tzinfo=UTC))
        UserSQLFactory(organization=organization)
        await db_session.flush()
        loaded = await repository.get_organization_by_id(organization_id=organization.id)

        # Act
        result = await repository.update_organization(organization=loaded.with_name("Renamed Org"))

        # Assert
        assert isinstance(result, Organization)
        assert result.id == organization.id
        assert result.name == "Renamed Org"
        assert result.users == 1
        assert result.updated > loaded.updated

        stored = await db_session.scalar(select(OrganizationTable).where(OrganizationTable.id == organization.id))
        assert stored.name == "Renamed Org"

    async def test_update_organization_should_return_not_found_error_when_organization_does_not_exist(self, repository, db_session):
        # Arrange
        organization = OrganizationSQLFactory(name="Org Used As Template")
        await db_session.flush()
        loaded = await repository.get_organization_by_id(organization_id=organization.id)

        # Act
        result = await repository.update_organization(organization=loaded.model_copy(update={"id": 999999}))

        # Assert
        assert isinstance(result, OrganizationNotFoundError)
        assert result.id == 999999

    async def test_update_organization_should_return_already_exists_error_when_name_is_duplicate(self, repository, db_session):
        # Arrange
        OrganizationSQLFactory(name="Existing Org")
        organization = OrganizationSQLFactory(name="Org To Rename Into Duplicate")
        await db_session.flush()
        loaded = await repository.get_organization_by_id(organization_id=organization.id)

        # Act
        result = await repository.update_organization(organization=loaded.with_name("Existing Org"))

        # Assert
        assert isinstance(result, OrganizationAlreadyExistsError)
        assert result.name == "Existing Org"
