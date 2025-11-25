from typing import Literal

from sqlalchemy import Integer, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.sql.models import User as UserTable
from api.utils.exceptions import UserNotFoundException


class PostgresUserRepository(UserRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_users(
        self,
        email: str | None = None,
        user_id: int | None = None,
        role_id: int | None = None,
        organization_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "email", "created", "updated"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[User]:
        statement = (
            select(
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
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )
        if email is not None:
            statement = statement.where(UserTable.email == email)
        if user_id is not None:
            statement = statement.where(UserTable.id == user_id)
        if role_id is not None:
            statement = statement.where(UserTable.role_id == role_id)
        if organization_id is not None:
            statement = statement.where(UserTable.organization_id == organization_id)

        result = await self.postgres_session.execute(statement=statement)
        users = [User(**row._mapping) for row in result.all()]

        if (user_id is not None or email is not None) and len(users) == 0:
            raise UserNotFoundException()

        return users
