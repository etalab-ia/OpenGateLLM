from typing import Literal

import bcrypt
from sqlalchemy import Integer, cast, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError
from api.infrastructure.postgres.decorators import with_lock
from api.sql.models import Permission as PermissionTable
from api.sql.models import User as UserTable
from api.utils.exceptions import UserNotFoundException


def _unix_timestamp(column):
    return cast(func.extract("epoch", column), Integer)


class PostgresUserRepository(UserRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _row_to_user(row) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            sub=row.sub,
            iss=row.iss,
            role=row.role,
            organization=row.organization,
            budget=row.budget,
            priority=row.priority,
            expires=row.expires,
            created=row.created,
            updated=row.updated,
        )

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @with_lock(namespace="user", key="email")
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
        hashed_password = self._hash_password(password=password)
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
                    _unix_timestamp(UserTable.expires).label("expires"),
                    _unix_timestamp(UserTable.created).label("created"),
                    _unix_timestamp(UserTable.updated).label("updated"),
                    UserTable.priority,
                )
            )
            row = result.one()
        except IntegrityError as e:
            if "user_organization_id_fkey" in str(e.orig):
                return OrganizationNotFoundError(id=organization_id)
            if "user_role_id_fkey" in str(e.orig):
                return RoleNotFoundError(id=role_id)
            return UserAlreadyExistsError(email=email)

        return self._row_to_user(row)

    async def get_first_admin_user(self) -> User | UserNotFoundError:
        result = await self.postgres_session.execute(
            select(
                UserTable.id,
                UserTable.email,
                UserTable.name,
                UserTable.sub,
                UserTable.iss,
                UserTable.role_id.label("role"),
                UserTable.organization_id.label("organization"),
                UserTable.budget,
                _unix_timestamp(UserTable.expires).label("expires"),
                _unix_timestamp(UserTable.created).label("created"),
                _unix_timestamp(UserTable.updated).label("updated"),
                UserTable.priority,
            )
            .join(PermissionTable, UserTable.role_id == PermissionTable.role_id)
            .where(PermissionTable.permission == PermissionType.ADMIN)
            .order_by(UserTable.id.asc())
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError()
        return self._row_to_user(row)

    async def get_user_by_email(self, email: str) -> User | UserNotFoundError:
        result = await self.postgres_session.execute(
            select(
                UserTable.id,
                UserTable.email,
                UserTable.name,
                UserTable.sub,
                UserTable.iss,
                UserTable.role_id.label("role"),
                UserTable.organization_id.label("organization"),
                UserTable.budget,
                _unix_timestamp(UserTable.expires).label("expires"),
                _unix_timestamp(UserTable.created).label("created"),
                _unix_timestamp(UserTable.updated).label("updated"),
                UserTable.priority,
            ).where(UserTable.email == email)
        )
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(email=email)
        return self._row_to_user(row)

    async def get_users(  # @TODO: remove this method after clean archi refactor
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
                UserTable.sub,
                UserTable.iss,
                UserTable.role_id.label("role"),
                UserTable.organization_id.label("organization"),
                UserTable.budget,
                _unix_timestamp(UserTable.expires).label("expires"),
                _unix_timestamp(UserTable.created).label("created"),
                _unix_timestamp(UserTable.updated).label("updated"),
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
        users = [self._row_to_user(row) for row in result.all()]

        if (user_id is not None or email is not None) and len(users) == 0:
            # TODO: change this to return the error and raise it in the use case instead of raising it here
            raise UserNotFoundException()

        return users

    @with_lock(namespace="user", key="user.id")
    async def update_user(self, user: User) -> User | UserNotFoundError | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        expires_value = func.to_timestamp(user.expires) if user.expires is not None else None

        statement = (
            update(table=UserTable)
            .values(
                email=user.email,
                name=user.name,
                sub=user.sub,
                iss=user.iss,
                role_id=user.role,
                organization_id=user.organization,
                budget=user.budget,
                expires=expires_value,
                priority=user.priority,
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
                _unix_timestamp(UserTable.expires).label("expires"),
                _unix_timestamp(UserTable.created).label("created"),
                _unix_timestamp(UserTable.updated).label("updated"),
                UserTable.priority,
            )
            .where(UserTable.id == user.id)
        )
        try:
            result = await self.postgres_session.execute(statement)
            row = result.one_or_none()
        except IntegrityError as e:
            if "user_organization_id_fkey" in str(e.orig):
                return OrganizationNotFoundError(id=user.organization)
            if "user_role_id_fkey" in str(e.orig):
                return RoleNotFoundError(id=user.role)
            if "ix_user_email_key" in str(e.orig):
                return UserAlreadyExistsError(email=user.email)

        if row is None:
            return UserNotFoundError(user_id=user.id)
        return self._row_to_user(row)

    async def delete_user(self, user_id: int) -> User | UserNotFoundError:
        raise NotImplementedError
