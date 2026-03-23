from typing import Literal

import bcrypt
from sqlalchemy import Integer, cast, exists, func, insert, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import User as UserTable
from api.utils.exceptions import UserNotFoundException


class PostgresUserRepository(UserRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def has_admin_user(self) -> bool:
        result = await self.postgres_session.execute(
            select(
                exists(
                    select(UserTable.id)
                    .join(PermissionTable, UserTable.role_id == PermissionTable.role_id)
                    .where(PermissionTable.permission == PermissionType.ADMIN)
                )
            )
        )
        return result.scalar()

    async def create_user(
        self,
        email: str,
        password: str,
        role_id: int,
        name: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: int | None = None,
        priority: int = 0,
    ) -> User | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        result = await self.postgres_session.execute(select(RoleTable.id).where(RoleTable.id == role_id))
        try:
            result.scalar_one()
        except NoResultFound:
            return RoleNotFoundError(role_id=role_id)

        if organization_id is not None:
            result = await self.postgres_session.execute(select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
            try:
                result.scalar_one()
            except NoResultFound:
                return OrganizationNotFoundError(organization_id=organization_id)

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        expires_value = func.to_timestamp(expires) if expires is not None else None

        try:
            result = await self.postgres_session.execute(
                insert(UserTable)
                .values(
                    email=email,
                    name=name,
                    password=hashed_password,
                    sub=sub,
                    iss=iss,
                    role_id=role_id,
                    organization_id=organization_id,
                    budget=budget,
                    expires=expires_value,
                    priority=priority,
                )
                .returning(
                    UserTable.id,
                    UserTable.email,
                    UserTable.name,
                    UserTable.sub,
                    UserTable.iss,
                    UserTable.role_id.label("role"),
                    UserTable.organization_id.label("organization"),
                    UserTable.budget,
                    cast(func.extract("epoch", UserTable.expires), Integer).label("expires"),
                    cast(func.extract("epoch", UserTable.created), Integer).label("created"),
                    cast(func.extract("epoch", UserTable.updated), Integer).label("updated"),
                    UserTable.priority,
                )
            )
            row = result.one()
        except IntegrityError:
            return UserAlreadyExistsError(email=email)

        return User(**row._mapping)

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
            # TODO: change this to return the error and raise it in the use case instead of raising it here
            raise UserNotFoundException()

        return users

    async def update_user(self, user: User) -> User:
        raise NotImplementedError

    async def delete_user(self, user_id: int) -> None:
        raise NotImplementedError
