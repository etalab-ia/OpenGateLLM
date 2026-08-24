from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError
from api.sql.models import Organization as OrganizationTable
from api.sql.models import User as UserTable


class PostgresOrganizationRepository(OrganizationRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def create_organization(self, name: str) -> Organization | OrganizationAlreadyExistsError:
        try:
            result = await self.postgres_session.execute(insert(OrganizationTable).values(name=name).returning(OrganizationTable))
            row = result.scalar_one()
        except IntegrityError as e:
            if "organization_name_key" in str(e.orig):
                return OrganizationAlreadyExistsError(name=name)
            raise

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
