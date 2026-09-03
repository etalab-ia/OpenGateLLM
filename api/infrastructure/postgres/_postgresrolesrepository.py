from sqlalchemy import asc, delete, desc, distinct, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.domain import SortField, SortOrder
from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role, RolePage
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.infrastructure.postgres.decorators import with_lock
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable


class PostgresRolesRepository(RoleRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _row_to_role(row, *, users: int = 0, permissions: list[PermissionType] | None = None, limits: list[Limit] | None = None) -> Role:
        return Role(
            id=row.id,
            name=row.name,
            created=row.created,
            updated=row.updated,
            users=users,
            permissions=permissions or [],
            limits=limits or [],
        )

    async def get_roles_page(
        self, limit: int = 10, offset: int = 0, sort_by: SortField = SortField.ID, sort_order: SortOrder = SortOrder.ASC
    ) -> RolePage:
        sort_column = {SortField.ID: RoleTable.id, SortField.NAME: RoleTable.name, SortField.CREATED: RoleTable.created}[sort_by]
        order_fn = asc if sort_order == SortOrder.ASC else desc
        role_query = (
            select(
                RoleTable.id,
                RoleTable.name,
                RoleTable.created,
                RoleTable.updated,
                func.count(distinct(UserTable.id)).label("users"),
            )
            .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
            .group_by(RoleTable.id)
            .order_by(order_fn(sort_column))
            .offset(offset)
            .limit(limit)
        )

        count_query = select(func.count()).select_from(RoleTable)
        total = (await self.postgres_session.execute(count_query)).scalar_one()

        result = await self.postgres_session.execute(role_query)
        roles = [self._row_to_role(row, users=row.users) for row in result.all()]

        return RolePage(total=total, data=roles)

    @with_lock(namespace="role", key="name")
    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        try:
            result = await self.postgres_session.execute(
                insert(RoleTable)
                .values(name=name)
                .returning(
                    RoleTable.id,
                    RoleTable.name,
                    RoleTable.created,
                    RoleTable.updated,
                )
            )
            row = result.one()
        except IntegrityError as e:
            if "ix_role_name" in str(e.orig):
                return RoleAlreadyExistsError(name=name)
            raise

        return self._row_to_role(row)

    async def get_role_with_permissions_and_limits_by_id(self, role_id: int) -> Role | RoleNotFoundError:
        users_subquery = select(func.count(UserTable.id)).where(UserTable.role_id == RoleTable.id).correlate(RoleTable).scalar_subquery()
        statement = (
            select(RoleTable, users_subquery.label("users"))
            .options(selectinload(RoleTable.permissions), selectinload(RoleTable.limits))
            .where(RoleTable.id == role_id)
        )
        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return RoleNotFoundError(id=role_id)
        role_row, users_count = row
        return self._row_to_role(
            role_row,
            users=users_count,
            permissions=[permission.permission for permission in role_row.permissions],
            limits=[Limit(router_id=limit.router_id, type=limit.type, value=limit.value) for limit in role_row.limits],
        )

    async def get_role_with_permissions_and_limits_by_name(self, role_name: str) -> Role | RoleNotFoundError:
        users_subquery = select(func.count(UserTable.id)).where(UserTable.role_id == RoleTable.id).correlate(RoleTable).scalar_subquery()
        statement = (
            select(RoleTable, users_subquery.label("users"))
            .options(selectinload(RoleTable.permissions), selectinload(RoleTable.limits))
            .where(RoleTable.name == role_name)
        )
        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return RoleNotFoundError(name=role_name)
        role_row, users_count = row
        return self._row_to_role(
            role_row,
            users=users_count,
            permissions=[permission.permission for permission in role_row.permissions],
            limits=[Limit(router_id=limit.router_id, type=limit.type, value=limit.value) for limit in role_row.limits],
        )

    @with_lock(namespace="role", key="role.id")
    async def update_role(self, role: Role) -> Role | RoleAlreadyExistsError | RoleNotFoundError:
        statement = (
            update(table=RoleTable)
            .values(name=role.name)
            .returning(
                RoleTable.id,
                RoleTable.name,
                RoleTable.created,
                RoleTable.updated,
            )
            .where(RoleTable.id == role.id)
        )
        try:
            result = await self.postgres_session.execute(statement)
            row = result.one_or_none()
        except IntegrityError:
            return RoleAlreadyExistsError(name=role.name)
        if row is None:
            return RoleNotFoundError(id=role.id)
        return self._row_to_role(row, permissions=role.permissions, limits=role.limits)

    @with_lock(namespace="role", key="role_id")
    async def delete_role(self, role_id: int) -> Role | RoleNotFoundError:
        result = await self.postgres_session.execute(
            delete(RoleTable)
            .where(RoleTable.id == role_id)
            .returning(
                RoleTable.id,
                RoleTable.name,
                RoleTable.created,
                RoleTable.updated,
            )
        )
        row = result.one_or_none()
        if row is None:
            return RoleNotFoundError(id=role_id)
        return self._row_to_role(row)
