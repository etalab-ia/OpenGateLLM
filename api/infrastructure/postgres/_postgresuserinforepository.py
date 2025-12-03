from sqlalchemy import Integer, cast, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.user.entities import User
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.entities import UserInfo
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable
from api.utils.exceptions import RoleNotFoundException, UserNotFoundException


class PostgresUserInfoRepository(UserInfoRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_user_info(self, user_id: int | None = None, email: str | None = None) -> UserInfo:
        assert user_id is not None or email is not None, "user_id or email is required"

        if user_id == 0:  # master user
            user = UserInfo(
                id=0,
                email="master",
                name="master",
                organization=0,
                budget=None,
                permissions=[],
                limits=[],
                expires=None,
                created=0,
                updated=0,
                priority=0,
            )
        else:
            statement = select(
                UserTable.id,
                UserTable.email,
                UserTable.name,
                UserTable.role_id.label("role"),
                UserTable.organization_id.label("organization"),
                UserTable.budget,
                cast(func.extract("epoch", UserTable.expires), Integer).label("expires"),
                cast(func.extract("epoch", UserTable.created), Integer).label("created"),
                cast(func.extract("epoch", UserTable.updated), Integer).label("updated"),
                UserTable.email,
                UserTable.sub,
                UserTable.priority,
            )
            if email is not None:
                statement = statement.where(UserTable.email == email)
            if user_id is not None:
                statement = statement.where(UserTable.id == user_id)

            result = await self.postgres_session.execute(statement=statement)
            users = [User(**row._mapping) for row in result.all()]

            if len(users) == 0:
                raise UserNotFoundException()
            user = users[0]

            role_query = (
                select(
                    RoleTable.id,
                    RoleTable.name,
                    cast(func.extract("epoch", RoleTable.created), Integer).label("created"),
                    cast(func.extract("epoch", RoleTable.updated), Integer).label("updated"),
                    func.count(distinct(UserTable.id)).label("users"),
                )
                .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
                .where(RoleTable.id.in_([user.role]))
                .group_by(RoleTable.id)
            )

            result = await self.postgres_session.execute(role_query)
            role_results = [row._asdict() for row in result.all()]

            if len(role_results) == 0:
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

            roles = list(roles.values())
            role = roles[0]

            # user cannot see limits on models that are not accessible by the role
            limits = [limit for limit in role.limits if limit.value is None or limit.value > 0]

            user = UserInfo(
                id=user.id,
                email=user.email,
                name=user.name,
                organization=user.organization,
                budget=user.budget,
                permissions=role.permissions,
                limits=limits,
                expires=user.expires,
                created=user.created,
                updated=user.updated,
                priority=user.priority,
            )

        return user
