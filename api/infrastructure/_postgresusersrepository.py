from typing import Literal

from sqlalchemy import Integer, cast, func, select
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
        # Mapping sécurisé des colonnes pour éviter l'injection SQL
        order_by_columns = {
            "id": UserTable.id,
            "email": UserTable.email,
            "created": UserTable.created,
            "updated": UserTable.updated,
        }

        # Validation et récupération de la colonne (avec valeur par défaut sécurisée)
        column = order_by_columns.get(order_by, UserTable.id)

        # Validation de la direction (avec valeur par défaut sécurisée)
        direction = order_direction if order_direction in {"asc", "desc"} else "asc"

        # Application de l'ordre de tri de manière sécurisée
        order_clause = column.asc() if direction == "asc" else column.desc()

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
                UserTable.sub,
                UserTable.iss,
                UserTable.priority,
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(order_clause)
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
