from sqlalchemy import Integer, asc, cast, desc, distinct, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.domain import SortField, SortOrder
from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role, RolePage
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable


def _unix_timestamp(column):
    return cast(func.extract("epoch", column), Integer)


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
                _unix_timestamp(RoleTable.created).label("created"),
                _unix_timestamp(RoleTable.updated).label("updated"),
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

    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        try:
            result = await self.postgres_session.execute(
                insert(RoleTable)
                .values(name=name)
                .returning(
                    RoleTable.id,
                    RoleTable.name,
                    _unix_timestamp(RoleTable.created).label("created"),
                    _unix_timestamp(RoleTable.updated).label("updated"),
                )
            )
            row = result.one()
        except IntegrityError:
            return RoleAlreadyExistsError(name=name)

        return self._row_to_role(row)

    async def get_full_role_by_id(self, role_id: int) -> Role | None:
        users_subquery = select(func.count(UserTable.id)).where(UserTable.role_id == RoleTable.id).correlate(RoleTable).scalar_subquery()
        statement = (
            select(RoleTable, users_subquery.label("users"))
            .options(selectinload(RoleTable.permissions), selectinload(RoleTable.limits))
            .where(RoleTable.id == role_id)
        )
        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return None
        role_row, users_count = row
        return Role(
            id=role_row.id,
            name=role_row.name,
            permissions=[p.permission for p in role_row.permissions],
            limits=[Limit(router_id=limit.router_id, type=limit.type, value=limit.value) for limit in role_row.limits],
            users=users_count,
            created=int(role_row.created.timestamp()),
            updated=int(role_row.updated.timestamp()),
        )

    async def update_role(self, role: Role) -> Role | RoleAlreadyExistsError | RoleNotFoundError:
        statement = (
            update(table=RoleTable)
            .values(name=role.name)
            .returning(
                RoleTable.id,
                RoleTable.name,
                _unix_timestamp(RoleTable.created).label("created"),
                _unix_timestamp(RoleTable.updated).label("updated"),
            )
            .where(RoleTable.id == role.id)
        )
        try:
            result = await self.postgres_session.execute(statement)
            row = result.one_or_none()
        except IntegrityError:
            return RoleAlreadyExistsError(name=role.name)
        if row is None:
            return RoleNotFoundError(role_id=role.id)
        return self._row_to_role(row, permissions=role.permissions, limits=role.limits)

    async def delete_role(self, role_id: int) -> None:
        raise NotImplementedError
