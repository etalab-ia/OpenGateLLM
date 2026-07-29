from typing import Any

from sqlalchemy import Integer, cast, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain import SortOrder
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User, UserPage, UserSortField
from api.domain.user.errors import (
    DeleteUserWithProvidersError,
    DeleteUserWithRoutersError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from api.infrastructure.postgres.decorators import with_lock
from api.sql.models import Permission as PermissionTable
from api.sql.models import User as UserTable


def _unix_timestamp(column):
    return cast(func.extract("epoch", column), Integer)


_USER_COLUMNS = (
    UserTable.id,
    UserTable.email,
    UserTable.name,
    UserTable.password,
    UserTable.sub,
    UserTable.iss,
    UserTable.claims,
    UserTable.role_id.label("role"),
    UserTable.organization_id.label("organization"),
    UserTable.budget,
    _unix_timestamp(UserTable.expires).label("expires"),
    _unix_timestamp(UserTable.created).label("created"),
    _unix_timestamp(UserTable.updated).label("updated"),
    UserTable.priority,
)


class PostgresUserRepository(UserRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _row_to_user(row) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            password=row.password,
            sub=row.sub,
            iss=row.iss,
            claims=row.claims,
            role=row.role,
            organization_id=row.organization,
            budget=row.budget,
            priority=row.priority,
            expires=row.expires,
            created=row.created,
            updated=row.updated,
        )

    async def get_user_by_id(self, user_id: int) -> User | UserNotFoundError:
        result = await self.postgres_session.execute(select(*_USER_COLUMNS).where(UserTable.id == user_id))
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(id=user_id)
        return self._row_to_user(row)

    @with_lock(namespace="user", key="email")
    async def create_user(
        self,
        email: str,
        role_id: int,
        password: str | None = None,
        name: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        claims: dict[str, Any] | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: int | None = None,
        priority: int = 0,
    ) -> User | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        expires_value = func.to_timestamp(expires) if expires is not None else None

        try:
            result = await self.postgres_session.execute(
                insert(UserTable)
                .values(
                    email=email,
                    name=name,
                    password=password,
                    claims=claims,
                    sub=sub,
                    iss=iss,
                    role_id=role_id,
                    organization_id=organization_id,
                    budget=budget,
                    expires=expires_value,
                    priority=priority,
                )
                .returning(*_USER_COLUMNS)
            )
            row = result.one()
        except IntegrityError as e:
            if "user_organization_id_fkey" in str(e.orig):
                return OrganizationNotFoundError(id=organization_id)
            if "user_role_id_fkey" in str(e.orig):
                return RoleNotFoundError(id=role_id)
            if "ix_user_email" in str(e.orig) or "unique_user_sub_iss" in str(e.orig):
                return UserAlreadyExistsError(email=email)
            raise

        return self._row_to_user(row)

    async def get_first_admin_user(self) -> User | UserNotFoundError:
        result = await self.postgres_session.execute(
            select(*_USER_COLUMNS)
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
        result = await self.postgres_session.execute(select(*_USER_COLUMNS).where(UserTable.email == email))
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(email=email)
        return self._row_to_user(row)

    async def get_user_by_iss_and_sub(self, iss: str, sub: str) -> User | UserNotFoundError:
        result = await self.postgres_session.execute(select(*_USER_COLUMNS).where(UserTable.iss == iss, UserTable.sub == sub))
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError()
        return self._row_to_user(row)

    async def get_users(
        self,
        role_id: int | None = None,
        organization_id: int | None = None,
        email: str | None = None,
        offset: int = 0,
        limit: int = 10,
        sort_by: UserSortField = UserSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> UserPage:
        order_by_columns = {
            "id": UserTable.id,
            "email": UserTable.email,
            "created": UserTable.created,
            "updated": UserTable.updated,
        }

        column = order_by_columns[sort_by]
        order_clause = column.asc() if sort_order == SortOrder.ASC else column.desc()

        count_query = select(func.count()).select_from(UserTable)

        statement = select(*_USER_COLUMNS).offset(offset=offset).limit(limit=limit).order_by(order_clause)
        conditions = []
        if role_id is not None:
            conditions.append(UserTable.role_id == role_id)
        if organization_id is not None:
            conditions.append(UserTable.organization_id == organization_id)
        if email is not None:
            conditions.append(UserTable.email.like(f"%{email.lower()}%"))

        total = (await self.postgres_session.execute(count_query.where(*conditions))).scalar_one()

        result = await self.postgres_session.execute(statement=statement.where(*conditions))
        users = [self._row_to_user(row) for row in result.all()]

        return UserPage(total=total, data=users)

    @with_lock(namespace="user", key="user.id")
    async def update_user(self, user: User) -> User | UserNotFoundError | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        expires_value = func.to_timestamp(user.expires) if user.expires is not None else None

        statement = (
            update(table=UserTable)
            .values(
                email=user.email,
                name=user.name,
                password=user.password.get_secret_value() if user.password is not None else None,
                sub=user.sub,
                iss=user.iss,
                claims=user.claims,
                role_id=user.role,
                organization_id=user.organization_id,
                budget=user.budget,
                expires=expires_value,
                priority=user.priority,
            )
            .returning(*_USER_COLUMNS)
            .where(UserTable.id == user.id)
        )
        try:
            result = await self.postgres_session.execute(statement)
            row = result.one_or_none()
        except IntegrityError as e:
            if "user_organization_id_fkey" in str(e.orig):
                return OrganizationNotFoundError(id=user.organization_id)
            if "user_role_id_fkey" in str(e.orig):
                return RoleNotFoundError(id=user.role)
            if "ix_user_email" in str(e.orig) or "unique_user_sub_iss" in str(e.orig):
                return UserAlreadyExistsError(email=user.email)
            raise

        if row is None:
            return UserNotFoundError(id=user.id)
        return self._row_to_user(row)

    async def delete_user(self, user_id: int) -> User | UserNotFoundError | DeleteUserWithRoutersError | DeleteUserWithProvidersError:
        try:
            async with self.postgres_session.begin_nested():
                result = await self.postgres_session.execute(statement=delete(UserTable).where(UserTable.id == user_id).returning(*_USER_COLUMNS))
        except IntegrityError as e:
            if "router_user_id_fkey" in str(e.orig):
                return DeleteUserWithRoutersError(user_id=user_id, router_ids=None)
            if "provider_user_id_fkey" in str(e.orig):
                return DeleteUserWithProvidersError(user_id=user_id, provider_ids=None)
            raise

        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(id=user_id)

        return self._row_to_user(row)

    async def get_user_id_and_password_by_email(self, email: str) -> tuple[int, str | None] | UserNotFoundError:
        result = await self.postgres_session.execute(select(UserTable.id, UserTable.password).where(UserTable.email == email))
        row = result.one_or_none()
        if row is None:
            return UserNotFoundError(email=email)

        return row.id, row.password
