from typing import Literal

from sqlalchemy import Integer, cast, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable
from api.utils.exceptions import RoleNotFoundException


class PostgresRolesRepository(RoleRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

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
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit).order_by(text(f"{order_by} {order_direction}"))
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
            .order_by(text(f"{order_by} {order_direction}"))
        )

        result = await self.postgres_session.execute(role_query)
        role_results = [row._asdict() for row in result.all()]

        if role_id is not None and len(role_results) == 0:
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
                    roles[role_id].limits.append(Limit(router=row.router_id, type=row.type, value=row.value))

            # Query permissions for these roles
            permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(list(roles.keys())))

            result = await self.postgres_session.execute(permissions_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].permissions.append(PermissionType(value=row.permission))

        return list(roles.values())
