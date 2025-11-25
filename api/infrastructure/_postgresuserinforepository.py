from sqlalchemy import Integer, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role import Limit
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.entities import UserInfo
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable


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
            query = (
                select(
                    UserTable.id,
                    UserTable.email,
                    UserTable.name,
                    UserTable.organization_id.label("organization"),
                    UserTable.budget,
                    UserTable.priority,
                    cast(func.extract("epoch", UserTable.expires), Integer).label("expires"),
                    cast(func.extract("epoch", UserTable.created), Integer).label("created"),
                    cast(func.extract("epoch", UserTable.updated), Integer).label("updated"),
                    func.array_agg(distinct(PermissionTable.permission)).label("permissions"),
                    func.array_agg(
                        distinct(
                            func.json_build_object(
                                "router",
                                LimitTable.router_id,
                                "type",
                                LimitTable.type,
                                "value",
                                LimitTable.value,
                            )
                        )
                    )
                    .filter(LimitTable.id.is_not(None))
                    .label("limits"),
                )
                .outerjoin(RoleTable, RoleTable.id == UserTable.role_id)
                .outerjoin(PermissionTable, PermissionTable.role_id == RoleTable.id)
                .outerjoin(LimitTable, LimitTable.role_id == RoleTable.id)
                .group_by(UserTable.id)
            )

            if user_id is not None:
                query = query.where(UserTable.id == user_id)
            if email is not None:
                query = query.where(UserTable.email == email)

            result = await self.postgres_session.execute(query)
            results = [row._asdict() for row in result.all()]

            if not results:
                raise ValueError("User not found")

            row = results[0]
            limits = [Limit(**limit) for limit in (row["limits"] or []) if limit["value"] is None or limit["value"] > 0]

            user = UserInfo(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                organization=row["organization"],
                budget=row["budget"],
                permissions=row["permissions"] or [],
                limits=limits,
                expires=row["expires"],
                created=row["created"],
                updated=row["updated"],
                priority=row["priority"],
            )

        return user
