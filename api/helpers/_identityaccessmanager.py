import datetime as dt
from datetime import datetime, timedelta
from typing import List, Literal, Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, distinct, insert, or_, select, text, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
import bcrypt

from api.schemas.admin.organizations import Organization
from api.schemas.admin.roles import Limit, PermissionType, Role
from api.schemas.admin.tokens import Token
from api.schemas.admin.users import User
from api.sql.models import Limit as LimitTable
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import Token as TokenTable
from api.sql.models import Usage as UsageTable
from api.sql.models import User as UserTable
from api.utils.exceptions import (
    DeleteRoleWithUsersException,
    InvalidTokenExpirationException,
    OrganizationNotFoundException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)


class IdentityAccessManager:
    TOKEN_PREFIX = "sk-"

    def __init__(self, master_key: str, max_token_expiration_days: Optional[int] = None):
        self.master_key = master_key
        self.max_token_expiration_days = max_token_expiration_days

    def _decode_token(self, token: str) -> dict:
        token = token.split(IdentityAccessManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=self.master_key, algorithms=["HS256"])

    def _encode_token(self, user_id: int, token_id: int, expires_at: Optional[int] = None) -> str:
        return IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires_at": expires_at},
            key=self.master_key,
            algorithm="HS256",
        )

    async def create_role(
        self,
        session: AsyncSession,
        name: str,
        limits: List[Limit] = None,
        permissions: List[PermissionType] = None,
    ) -> int:
        if limits is None:
            limits = []

        if permissions is None:
            permissions = []

        # create the role
        try:
            result = await session.execute(statement=insert(table=RoleTable).values(name=name).returning(RoleTable.id))
            role_id = result.scalar_one()
            await session.commit()
        except IntegrityError:
            raise RoleAlreadyExistsException()

        # create the limits
        for limit in limits:
            await session.execute(statement=insert(table=LimitTable).values(role_id=role_id, model=limit.model, type=limit.type, value=limit.value))  # fmt: off

        # create the permissions
        for permission in permissions:
            await session.execute(statement=insert(table=PermissionTable).values(role_id=role_id, permission=permission))

        await session.commit()

        return role_id

    async def delete_role(self, session: AsyncSession, role_id: int) -> None:
        # check if role exists
        result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # delete the role
        try:
            await session.execute(statement=delete(table=RoleTable).where(RoleTable.id == role_id))
        except IntegrityError:
            raise DeleteRoleWithUsersException()

        await session.commit()

    async def update_role(
        self,
        session: AsyncSession,
        role_id: int,
        name: Optional[str] = None,
        limits: Optional[List[Limit]] = None,
        permissions: Optional[List[PermissionType]] = None,
    ) -> None:
        # check if role exists
        result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
        try:
            role = result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # update the role
        if name is not None:
            await session.execute(statement=update(table=RoleTable).values(name=name).where(RoleTable.id == role.id))

        if limits is not None:
            # delete the existing limits
            await session.execute(statement=delete(table=LimitTable).where(LimitTable.role_id == role.id))

            # create the new limits
            values = [{"role_id": role.id, "model": limit.model, "type": limit.type, "value": limit.value} for limit in limits]
            if values:
                await session.execute(statement=insert(table=LimitTable).values(values))

        if permissions is not None:
            # delete the existing permissions
            await session.execute(statement=delete(table=PermissionTable).where(PermissionTable.role_id == role.id))

            # Only insert if there are permissions to insert
            if permissions:
                values = [{"role_id": role.id, "permission": permission} for permission in set(permissions)]
                if values:
                    await session.execute(statement=insert(table=PermissionTable).values(values))

        await session.commit()

    async def get_roles(
        self,
        session: AsyncSession,
        role_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Role]:
        if role_id is None:
            # get the unique role IDs with pagination
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit).order_by(text(f"{order_by} {order_direction}"))
            result = await session.execute(statement=statement)
            selected_roles = [row[0] for row in result.all()]
        else:
            selected_roles = [role_id]

        # Query basic role data with user count
        role_query = (
            select(
                RoleTable.id,
                RoleTable.name,
                cast(func.extract("epoch", RoleTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", RoleTable.updated_at), Integer).label("updated_at"),
                func.count(distinct(UserTable.id)).label("users"),
            )
            .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
            .where(RoleTable.id.in_(selected_roles))
            .group_by(RoleTable.id)
            .order_by(text(f"{order_by} {order_direction}"))
        )

        result = await session.execute(role_query)
        role_results = [row._asdict() for row in result.all()]

        if role_id is not None and len(role_results) == 0:
            raise RoleNotFoundException()

        # Build roles dictionary
        roles = {}
        for row in role_results:
            roles[row["id"]] = Role(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                users=row["users"],
                limits=[],
                permissions=[],
            )

        # Query limits for these roles
        if roles:
            limits_query = select(LimitTable.role_id, LimitTable.model, LimitTable.type, LimitTable.value).where(
                LimitTable.role_id.in_(list(roles.keys()))
            )

            result = await session.execute(limits_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].limits.append(Limit(model=row.model, type=row.type, value=row.value))

            # Query permissions for these roles
            permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(list(roles.keys())))

            result = await session.execute(permissions_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].permissions.append(PermissionType(value=row.permission))

        return list(roles.values())

    async def create_user(
        self,
        session: AsyncSession,
        name: str,
        role_id: int,
        organization_id: Optional[int] = None,
        budget: Optional[float] = None,
        expires_at: Optional[int] = None,
        sub: Optional[str] = None,
        email: Optional[str] = None,
    ) -> int:
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

        # check if role exists
        result = await session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # check if organization exists
        if organization_id is not None:
            result = await session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise OrganizationNotFoundException()

        # create the user
        try:
            result = await session.execute(
                statement=insert(table=UserTable)
                .values(
                    name=name,
                    role_id=role_id,
                    organization_id=organization_id,
                    budget=budget,
                    expires_at=expires_at,
                    sub=sub,
                    email=email,
                )
                .returning(UserTable.id)
            )
            user_id = result.scalar_one()
        except IntegrityError as e:
            raise UserAlreadyExistsException(detail=str(e))

        await session.commit()

        return user_id

    async def delete_user(self, session: AsyncSession, user_id: int) -> None:
        # check if user exists
        result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # delete the user
        await session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
        await session.commit()

    async def update_user(
        self,
        session: AsyncSession,
        user_id: int,
        name: Optional[str] = None,
        role_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        budget: Optional[float] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        """
        Update user. Warning: budget, expires_at and organization_id are always replaced by the values passed as parameters because None is a valid value for these fields.

        Args:
            session: The session to use.
            user_id: The ID of the user to update.
            name: The new name of the user.
            role_id: The new role ID of the user.
            organization_id: The new organization ID of the user.
            budget: The new budget of the user.
            expires_at: The new expiration timestamp of the user.
        """
        # check if user exists
        result = await session.execute(
            statement=select(
                UserTable.id,
                UserTable.name,
                UserTable.role_id,
                UserTable.budget,
                UserTable.expires_at,
                RoleTable.name.label("role"),
            )
            .join(RoleTable, UserTable.role_id == RoleTable.id)
            .where(UserTable.id == user_id)
        )
        try:
            user = result.all()[0]
        except IndexError:
            raise UserNotFoundException()

        # update the user
        name = name if name is not None else user.name
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

        if role_id is not None and role_id != user.role_id:
            # check if role exists
            result = await session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()
        role_id = role_id if role_id is not None else user.role_id

        if organization_id is not None:
            result = await session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise OrganizationNotFoundException()

        await session.execute(
            statement=update(table=UserTable)
            .values(
                name=name,
                role_id=role_id,
                organization_id=organization_id,
                budget=budget,
                expires_at=expires_at,
            )
            .where(UserTable.id == user.id)
        )
        await session.commit()

    async def get_users(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        role_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[User]:
        statement = (
            select(
                UserTable.id,
                UserTable.name,
                UserTable.role_id.label("role"),
                UserTable.organization_id.label("organization"),
                UserTable.budget,
                cast(func.extract("epoch", UserTable.expires_at), Integer).label("expires_at"),
                cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
                UserTable.email,
                UserTable.sub,
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )
        if user_id is not None:
            statement = statement.where(UserTable.id == user_id)
        if role_id is not None:
            statement = statement.where(UserTable.role_id == role_id)
        if organization_id is not None:
            statement = statement.where(UserTable.organization_id == organization_id)

        result = await session.execute(statement=statement)
        users = [User(**row._mapping) for row in result.all()]

        if user_id is not None and len(users) == 0:
            raise UserNotFoundException()

        return users

    async def create_organization(self, session: AsyncSession, name: str) -> int:
        result = await session.execute(statement=insert(table=OrganizationTable).values(name=name).returning(OrganizationTable.id))
        organization_id = result.scalar_one()
        await session.commit()

        return organization_id

    async def delete_organization(self, session: AsyncSession, organization_id: int) -> None:
        result = await session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise OrganizationNotFoundException()

        await session.execute(statement=delete(table=OrganizationTable).where(OrganizationTable.id == organization_id))
        await session.commit()

    async def update_organization(self, session: AsyncSession, organization_id: int, name: Optional[str] = None) -> None:
        result = await session.execute(statement=select(OrganizationTable).where(OrganizationTable.id == organization_id))
        try:
            organization = result.scalar_one()
        except NoResultFound:
            raise OrganizationNotFoundException()

        if name is not None:
            await session.execute(statement=update(table=OrganizationTable).values(name=name).where(OrganizationTable.id == organization.id))
        await session.commit()

    async def get_organizations(
        self,
        session: AsyncSession,
        organization_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Organization]:
        statement = (
            select(
                OrganizationTable.id,
                OrganizationTable.name,
                cast(func.extract("epoch", OrganizationTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", OrganizationTable.updated_at), Integer).label("updated_at"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )

        if organization_id is not None:
            statement = statement.where(OrganizationTable.id == organization_id)

        result = await session.execute(statement=statement)
        organizations = [Organization(**row._mapping) for row in result.all()]

        if organization_id is not None and len(organizations) == 0:
            raise OrganizationNotFoundException()

        return organizations

    async def create_token(self, session: AsyncSession, user_id: int, name: str, expires_at: Optional[int] = None) -> Tuple[int, str]:
        # get the user id

        if self.max_token_expiration_days:
            if expires_at is None:
                expires_at = int(dt.datetime.now(tz=dt.UTC).timestamp()) + self.max_token_expiration_days * 86400
            elif expires_at > int(dt.datetime.now(tz=dt.UTC).timestamp()) + self.max_token_expiration_days * 86400:
                raise InvalidTokenExpirationException(detail=f"Token expiration timestamp cannot be greater than {self.max_token_expiration_days} days from now.")  # fmt: off

        result = await session.execute(statement=select(UserTable).where(UserTable.id == user_id))
        try:
            user = result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # create the token
        result = await session.execute(statement=insert(table=TokenTable).values(user_id=user.id, name=name).returning(TokenTable.id))
        token_id = result.scalar_one()
        await session.commit()

        # generate the token
        token = self._encode_token(user_id=user.id, token_id=token_id, expires_at=expires_at)

        # update the token
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
        await session.execute(
            statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires_at=expires_at).where(TokenTable.id == token_id)
        )
        await session.commit()

        return token_id, token

    async def refresh_token(self, session: AsyncSession, user_id: int, name: str, days: int = 1) -> Tuple[int, str]:
        """
        Create a new token with the same name, update Usage table references,
        and delete old tokens with the same name and user_id.

        Args:
            session: Database session
            user_id: ID of the user
            name: Name of the token to refresh
            days: Number of days the new token should be valid for

        Returns:
            Tuple containing the new token_id and app_token
        """
        # Get the old token_id for tokens with the same name and user_id
        old_token_result = await session.execute(statement=select(TokenTable.id).where(TokenTable.user_id == user_id, TokenTable.name == name))
        old_token_ids = [row[0] for row in old_token_result.all()]

        expires_at = int((datetime.now() + timedelta(days=days)).timestamp())
        # Create a new token
        new_token_id, app_token = await self.create_token(session, user_id, name, expires_at=expires_at)

        # Update Usage table to point to the new token_id for old token references
        if old_token_ids:
            await session.execute(statement=update(UsageTable).values(token_id=new_token_id).where(UsageTable.token_id.in_(old_token_ids)))

        # Delete all old tokens with the same name and user_id (excluding the newly created one)
        if old_token_ids:
            await session.execute(
                statement=delete(TokenTable).where(TokenTable.user_id == user_id, TokenTable.name == name, TokenTable.id.in_(old_token_ids))
            )
            await session.commit()

        return new_token_id, app_token

    async def delete_token(self, session: AsyncSession, user_id: int, token_id: int) -> None:
        # check if token exists
        result = await session.execute(statement=select(TokenTable.id).where(TokenTable.id == token_id).where(TokenTable.user_id == user_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise TokenNotFoundException()

        # delete the token
        await session.execute(statement=delete(table=TokenTable).where(TokenTable.id == token_id))
        await session.commit()

    async def delete_tokens(self, session: AsyncSession, user_id: int, name: str):
        """
        Delete tokens for a specific user, optionally filtered by token name

        Args:
            session: Database session
            user_id: ID of the user whose tokens should be deleted
            name: name filter for tokens to delete
        """
        query = delete(TokenTable).where(TokenTable.user_id == user_id).where(TokenTable.name == name)

        await session.execute(query)
        await session.commit()

    async def get_tokens(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        token_id: Optional[int] = None,
        exclude_expired: bool = False,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Token]:
        statement = (
            select(
                TokenTable.id,
                TokenTable.name,
                TokenTable.token,
                TokenTable.user_id.label("user"),
                cast(func.extract("epoch", TokenTable.expires_at), Integer).label("expires_at"),
                cast(func.extract("epoch", TokenTable.created_at), Integer).label("created_at"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )

        if user_id is not None:
            statement = statement.where(TokenTable.user_id == user_id)

        if token_id is not None:
            statement = statement.where(TokenTable.id == token_id)

        if exclude_expired is not None:
            statement = statement.where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))

        result = await session.execute(statement=statement)
        tokens = [Token(**row._mapping) for row in result.all()]

        if token_id is not None and len(tokens) == 0:
            raise TokenNotFoundException()

        return tokens

    async def check_token(self, session: AsyncSession, token: str) -> Tuple[Optional[int], Optional[int]]:
        try:
            claims = self._decode_token(token=token)
        except JWTError:
            return None, None
        except IndexError:  # malformed token (no token prefix)
            return None, None

        try:
            await self.get_tokens(session, user_id=claims["user_id"], token_id=claims["token_id"], exclude_expired=True, limit=1)
        except TokenNotFoundException:
            return None, None

        return claims["user_id"], claims["token_id"]

    async def invalidate_token(self, session: AsyncSession, token_id: int, user_id: int) -> None:
        """
        Invalidate a token by setting its expires_at to the current timestamp

        Args:
            session: Database session
            token_id: ID of the token to invalidate
            user_id: ID of the user who owns the token (for security)
        """
        await session.execute(update(TokenTable).where(TokenTable.id == token_id).where(TokenTable.user_id == user_id).values(expires_at=func.now()))
        await session.commit()

    async def get_user(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        sub: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        # Build conditions list only for non-None values
        conditions = []
        if user_id is not None:
            conditions.append(UserTable.id == user_id)
        if sub is not None:
            conditions.append(UserTable.sub == sub)
        if email is not None:
            conditions.append(UserTable.email == email)

        # If no conditions, return None
        if not conditions:
            return None

        # Build query with OR conditions
        query = select(UserTable).where(or_(*conditions))
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def verify_user_credentials(self, session: AsyncSession, email: str, password: str):
        """
        Verify playground credentials by matching playground_name (which maps to FastAPI user.email)
        and password against the FastAPI DB. Returns the UserTable ORM instance on success, None otherwise.
        """
        if not email or not password:
            return None

        # Look up user by email
        result = await session.execute(select(UserTable).where(UserTable.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return None

        stored_hashed = getattr(user, "password", None)
        if not stored_hashed:
            return None

        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hashed.encode("utf-8")):
                return user
        except Exception:
            return None

        return None

    async def change_password(self, session: AsyncSession, user_id: int, current_password: str, new_password: str) -> None:
        """Change the password for a user after verifying the current password."""
        # fetch user
        result = await session.execute(select(UserTable).where(UserTable.id == user_id))
        try:
            user = result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        stored_hashed = getattr(user, "password", None)
        if not stored_hashed:
            # No password set
            raise Exception("Current password is invalid")

        try:
            if not bcrypt.checkpw(current_password.encode("utf-8"), stored_hashed.encode("utf-8")):
                raise Exception("Current password is invalid")
        except Exception:
            raise Exception("Current password is invalid")

        # Hash new password and store it
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await session.execute(update(UserTable).where(UserTable.id == user_id).values(password=hashed))
        await session.commit()
