from sqlalchemy import Integer, Select, cast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from api.domain.role.entities import LimitType
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import UserWithRoleView
from api.sql.models import Limit as LimitTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import User as UserTable


class PostgresUserWithRoleQuery(UserWithRoleQuery):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_user_with_role_by_id(self, user_id: int) -> UserWithRoleView | UserNotFoundError:
        statement = self._build_statement()
        statement = statement.where(UserTable.id == user_id)

        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(id=user_id)

        return self._row_to_view(row)

    async def get_user_with_role_by_email(self, email: str) -> UserWithRoleView | UserNotFoundError:
        statement = self._build_statement()
        statement = statement.where(UserTable.email == email)

        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(email=email)

        return self._row_to_view(row)

    @staticmethod
    def _build_statement() -> Select:
        permissions_subquery = (
            select(func.array_agg(PermissionTable.permission))
            .where(PermissionTable.role_id == UserTable.role_id)
            .correlate(UserTable)
            .scalar_subquery()
            .label("permissions")
        )

        limits_subquery = (
            select(func.json_agg(func.json_build_object("router_id", LimitTable.router_id, "type", LimitTable.type, "value", LimitTable.value)))
            .where(LimitTable.role_id == UserTable.role_id)
            .correlate(UserTable)
            .scalar_subquery()
            .label("limits")
        )

        statement = select(
            UserTable.id,
            UserTable.email,
            UserTable.name,
            UserTable.organization_id.label("organization"),
            UserTable.budget,
            cast(func.extract("epoch", UserTable.expires), Integer).label("expires"),
            cast(func.extract("epoch", UserTable.created), Integer).label("created"),
            cast(func.extract("epoch", UserTable.updated), Integer).label("updated"),
            UserTable.priority,
            permissions_subquery,
            limits_subquery,
        )

        return statement

    @staticmethod
    def _row_to_view(row) -> UserWithRoleView:
        data = dict(row._mapping)
        data["permissions"] = data.get("permissions") or []
        data["limits"] = data.get("limits") or []
        for limit in data["limits"]:
            limit["type"] = LimitType[limit["type"]]

        return UserWithRoleView(**data)
