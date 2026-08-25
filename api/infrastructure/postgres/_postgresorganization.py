from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationHasUsersError, OrganizationNotFoundError
from api.infrastructure.postgres.decorators import with_lock
from api.sql.models import Organization as OrganizationTable
from api.sql.models import User as UserTable


class PostgresOrganizationRepository(OrganizationRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def create_organization(self, name: str) -> Organization | OrganizationAlreadyExistsError:
        try:
            result = await self.postgres_session.execute(insert(OrganizationTable).values(name=name).returning(OrganizationTable))
            row = result.scalar_one()
        except IntegrityError:
            return OrganizationAlreadyExistsError(name=name)

        return Organization(id=row.id, name=row.name, users=0, created=row.created, updated=row.updated)

    async def get_organization_by_name(self, name: str) -> Organization | OrganizationNotFoundError:
        users_subquery = (
            select(func.count(UserTable.id)).where(UserTable.organization_id == OrganizationTable.id).correlate(OrganizationTable).scalar_subquery()
        )
        statement = select(
            OrganizationTable,
            users_subquery.label("users"),
        ).where(OrganizationTable.name == name)
        result = await self.postgres_session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return OrganizationNotFoundError(name=name)

        row, users_count = row
        return Organization(id=row.id, name=row.name, users=users_count, created=row.created, updated=row.updated)

    async def get_organization_by_id(self, organization_id: int) -> Organization | OrganizationNotFoundError:
        users_subquery = (
            select(func.count(UserTable.id)).where(UserTable.organization_id == OrganizationTable.id).correlate(OrganizationTable).scalar_subquery()
        )
        statement = select(
            OrganizationTable,
            users_subquery.label("users"),
        ).where(OrganizationTable.id == organization_id)
        result = await self.postgres_session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return OrganizationNotFoundError(id=organization_id)

        row, users_count = row
        return Organization(id=row.id, name=row.name, users=users_count, created=row.created, updated=row.updated)

    @with_lock(namespace="organization", key="organization_id")
    async def delete_organization(self, organization_id: int) -> Organization | OrganizationNotFoundError | OrganizationHasUsersError:
        statement = (
            delete(OrganizationTable)
            .where(OrganizationTable.id == organization_id)
            .returning(OrganizationTable.id, OrganizationTable.name, OrganizationTable.created, OrganizationTable.updated)
        )
        try:
            # savepoint: a FK failure would otherwise poison the transaction and forbid the count query below
            async with self.postgres_session.begin_nested():
                result = await self.postgres_session.execute(statement)
        except IntegrityError as e:
            if "user_organization_id_fkey" in str(e.orig):
                users_count = await self.postgres_session.scalar(select(func.count(UserTable.id)).where(UserTable.organization_id == organization_id))
                return OrganizationHasUsersError(id=organization_id, number_of_users=users_count)
            raise
        row = result.one_or_none()
        if row is None:
            return OrganizationNotFoundError(id=organization_id)
        return Organization(id=row.id, name=row.name, users=0, created=row.created, updated=row.updated)
