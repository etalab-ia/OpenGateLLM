from typing import Literal

from sqlalchemy import Integer, asc, cast, desc, distinct, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.domain import SortField, SortOrder
from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role, RolePage
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable
from api.utils.exceptions import RoleNotFoundException


class PostgresRolesRepository(RoleRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_roles_page(
        self, limit: int = 10, offset: int = 0, sort_by: SortField = SortField.ID, sort_order: SortOrder = SortOrder.ASC
    ) -> RolePage:
        sort_column = {SortField.ID: RoleTable.id, SortField.NAME: RoleTable.name, SortField.CREATED: RoleTable.created}[sort_by]
        order_fn = asc if sort_order == SortOrder.ASC else desc
        role_query = (
            select(
                RoleTable.id,
                RoleTable.name,
                cast(func.extract("epoch", RoleTable.created), Integer).label("created"),
                cast(func.extract("epoch", RoleTable.updated), Integer).label("updated"),
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
        roles = [
            Role(
                id=row.id,
                name=row.name,
                created=row.created,
                updated=row.updated,
                users=row.users,
                limits=[],
                permissions=[],
            )
            for row in result.all()
        ]

        return RolePage(total=total, data=roles)

    async def create_role(self, name: str) -> Role | RoleAlreadyExistsError:
        try:
            result = await self.postgres_session.execute(
                insert(RoleTable)
                .values(name=name)
                .returning(
                    RoleTable.id,
                    RoleTable.name,
                    cast(func.extract("epoch", RoleTable.created), Integer).label("created"),
                    cast(func.extract("epoch", RoleTable.updated), Integer).label("updated"),
                )
            )
            row = result.one()
        except IntegrityError:
            return RoleAlreadyExistsError(name=name)

        return Role(
            id=row.id,
            name=row.name,
            permissions=[],
            limits=[],
            users=0,
            created=row.created,
            updated=row.updated,
        )

    async def get_roles(
        self,
        role_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created", "updated"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Role]:
        if role_id is None:
            # get the unique role IDs with pagination
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit).order_by(text(f"{order_by} {order_direction}"))  # nosemgrep
            result = await self.postgres_session.execute(statement=statement)
            selected_roles = [row[0] for row in result.all()]
        else:
            selected_roles = [role_id]

        # Query basic role data with user count
        role_query = (
            select(
                RoleTable.id,
                RoleTable.name,
                cast(func.extract("epoch", RoleTable.created), Integer).label("created"),
                cast(func.extract("epoch", RoleTable.updated), Integer).label("updated"),
                func.count(distinct(UserTable.id)).label("users"),
            )
            .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
            .where(RoleTable.id.in_(selected_roles))
            .group_by(RoleTable.id)
            .order_by(text(f"{order_by} {order_direction}"))  # nosemgrep
        )

        result = await self.postgres_session.execute(role_query)
        role_results = [row._asdict() for row in result.all()]

        if role_id is not None and len(role_results) == 0:
            # TODO: change this to return the error and raise it in the use case instead of raising it here
            raise RoleNotFoundException()

        # Build roles dictionary
        roles = {}
        for row in role_results:
            roles[row["id"]] = Role(
                id=row["id"],
                name=row["name"],
                created=row["created"],
                updated=row["updated"],
                users=row["users"],
                limits=[],
                permissions=[],
            )

        if roles:
            # Query limits for these roles
            limits_query = select(
                LimitTable.role_id,
                LimitTable.router_id,
                LimitTable.type,
                LimitTable.value,
            ).where(LimitTable.role_id.in_(list(roles.keys())))

            result = await self.postgres_session.execute(limits_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].limits.append(Limit(router_id=row.router_id, type=row.type, value=row.value))

            # Query permissions for these roles
            permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(list(roles.keys())))

            result = await self.postgres_session.execute(permissions_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].permissions.append(PermissionType(value=row.permission))

        return list(roles.values())

    async def get_role_by_id(self, role_id: int) -> Role | RoleNotFoundError:
        statement = select(RoleTable).options(selectinload(RoleTable.permissions), selectinload(RoleTable.limits)).where(RoleTable.id == role_id)
        result = await self.postgres_session.execute(statement=statement)
        row = result.scalar_one_or_none()
        if row is None:
            return RoleNotFoundError(role_id=role_id)
        return Role(
            id=row.id,
            name=row.name,
            permissions=[p.permission for p in row.permissions],
            limits=[Limit(router_id=limit.router_id, type=limit.type, value=limit.value) for limit in row.limits],
            created=int(row.created.timestamp()),
            updated=int(row.updated.timestamp()),
        )

    async def update_role(self, role: Role) -> Role | RoleAlreadyExistsError | RoleNotFoundError:
        statement = (
            update(table=RoleTable)
            .values(name=role.name)
            .returning(
                RoleTable.id,
                RoleTable.name,
                cast(func.extract("epoch", RoleTable.created), Integer).label("created"),
                cast(func.extract("epoch", RoleTable.updated), Integer).label("updated"),
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
        return Role(
            id=row.id,
            name=row.name,
            permissions=role.permissions,
            limits=role.limits,
            users=0,
            created=row.created,
            updated=row.updated,
        )

    async def delete_role(self, role_id: int) -> None:
        raise NotImplementedError
