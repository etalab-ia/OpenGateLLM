from sqlalchemy import asc, delete, desc, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain import SortOrder
from api.domain.organization import OrganizationRepository
from api.domain.organization.entities import Organization, OrganizationPage, OrganizationSortField
from api.domain.organization.errors import OrganizationAlreadyExistsError, OrganizationNotFoundError
from api.infrastructure.postgres._pagination import fetch_page_with_total
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

    async def get_organizations_page(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: OrganizationSortField = OrganizationSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> OrganizationPage:
        sort_column = {
            OrganizationSortField.ID: OrganizationTable.id,
            OrganizationSortField.NAME: OrganizationTable.name,
            OrganizationSortField.CREATED: OrganizationTable.created,
            OrganizationSortField.UPDATED: OrganizationTable.updated,
        }[sort_by]
        order_fn = asc if sort_order == SortOrder.ASC else desc

        users_subquery = (
            select(func.count(UserTable.id)).where(UserTable.organization_id == OrganizationTable.id).correlate(OrganizationTable).scalar_subquery()
        )
        organizations_query = (
            select(OrganizationTable, users_subquery.label("users"), func.count().over().label("total"))
            .order_by(order_fn(sort_column))
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(OrganizationTable)
        rows, total = await fetch_page_with_total(self.postgres_session, organizations_query, count_query)

        organizations = [
            Organization(id=row[0].id, name=row[0].name, users=row.users, created=row[0].created, updated=row[0].updated) for row in rows
        ]

        return OrganizationPage(total=total, data=organizations)

    @with_lock(namespace="organization", key="organization.id")
    async def update_organization(self, organization: Organization) -> Organization | OrganizationAlreadyExistsError | OrganizationNotFoundError:
        statement = (
            update(OrganizationTable)
            .where(OrganizationTable.id == organization.id)
            .values(name=organization.name)
            .returning(
                OrganizationTable.id,
                OrganizationTable.name,
                OrganizationTable.created,
                OrganizationTable.updated,
            )
        )
        try:
            result = await self.postgres_session.execute(statement)
            row = result.one_or_none()
        except IntegrityError as e:
            if "organization_name_key" in str(e.orig):
                return OrganizationAlreadyExistsError(name=organization.name)
            raise

        if row is None:
            return OrganizationNotFoundError(id=organization.id)

        return Organization(id=row.id, name=row.name, users=organization.users, created=row.created, updated=row.updated)

    @with_lock(namespace="organization", key="organization_id")
    async def delete_organization(self, organization_id: int) -> Organization | OrganizationNotFoundError:
        statement = (
            delete(OrganizationTable)
            .where(OrganizationTable.id == organization_id)
            .returning(OrganizationTable.id, OrganizationTable.name, OrganizationTable.created, OrganizationTable.updated)
        )
        result = await self.postgres_session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return OrganizationNotFoundError(id=organization_id)
        return Organization(id=row.id, name=row.name, users=0, created=row.created, updated=row.updated)
