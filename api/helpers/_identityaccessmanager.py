import datetime as dt
from datetime import datetime, timedelta
from typing import Literal

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, distinct, insert, or_, select, text, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from api.schemas.admin.organizations import Organization
from api.schemas.admin.roles import Limit, LimitType, PermissionType, Role
from api.schemas.admin.tokens import Token
from api.schemas.admin.users import User
from api.schemas.me.info import UserInfo
from api.sql.models import Limit as LimitTable
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Permission as PermissionTable
from api.sql.models import Role as RoleTable
from api.sql.models import Token as TokenTable
from api.sql.models import User as UserTable
from api.utils.configuration import configuration
from api.utils.context import global_context
from api.utils.exceptions import (
    DeleteOrganizationWithUsersException,
    DeleteRoleWithUsersException,
    InvalidCurrentPasswordException,
    InvalidTokenExpirationException,
    OrganizationNotFoundException,
    ReservedEmailException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)

settings = configuration.settings


class IdentityAccessManager:
    TOKEN_PREFIX = "sk-"
    PLAYGROUND_KEY_NAME = "playground"

    def __init__(self, master_key: str, key_max_expiration_days: int | None = None, playground_session_duration: int = 3600):
        self.master_key = master_key
        self.key_max_expiration_days = key_max_expiration_days
        self.playground_session_duration = playground_session_duration

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password=password.encode("utf-8"), salt=bcrypt.gensalt()).decode("utf-8")

    def _check_password(self, password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password=password.encode("utf-8"), hashed_password=hashed_password.encode("utf-8"))

    def _decode_token(self, token: str) -> dict:
        token = token.split(IdentityAccessManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=self.master_key, algorithms=["HS256"])

    def _encode_token(self, user_id: int, token_id: int, expires: int | None = None) -> str:
        return IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires": expires},
            key=self.master_key,
            algorithm="HS256",
        )

    async def create_role(
        self,
        postgres_session: AsyncSession,
        name: str,
        limits: list[Limit] = None,
        permissions: list[PermissionType] = None,
    ) -> int:
        if limits is None:
            limits = []

        if permissions is None:
            permissions = []

        # create the role
        try:
            result = await postgres_session.execute(statement=insert(table=RoleTable).values(name=name).returning(RoleTable.id))
            role_id = result.scalar_one()
            await postgres_session.commit()
        except IntegrityError:
            raise RoleAlreadyExistsException()

        # create the limits
        for limit in limits:
            await postgres_session.execute(statement=insert(table=LimitTable).values(role_id=role_id, router_id=limit.router, type=limit.type, value=limit.value))  # fmt: off

        # create the permissions
        for permission in permissions:
            await postgres_session.execute(statement=insert(table=PermissionTable).values(role_id=role_id, permission=permission))

        await postgres_session.commit()

        return role_id

    async def delete_role(self, postgres_session: AsyncSession, role_id: int) -> None:
        # check if role exists
        result = await postgres_session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # delete the role
        try:
            await postgres_session.execute(statement=delete(table=RoleTable).where(RoleTable.id == role_id))
        except IntegrityError:
            raise DeleteRoleWithUsersException()

        await postgres_session.commit()

    async def update_role(
        self,
        postgres_session: AsyncSession,
        role_id: int,
        name: str | None = None,
        limits: list[Limit] | None = None,
        permissions: list[PermissionType] | None = None,
    ) -> None:
        # check if role exists
        result = await postgres_session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
        try:
            role = result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # update the role
        if name is not None:
            await postgres_session.execute(statement=update(table=RoleTable).values(name=name).where(RoleTable.id == role.id))

        if limits is not None:
            # delete the existing limits
            await postgres_session.execute(statement=delete(table=LimitTable).where(LimitTable.role_id == role.id))

            # create the new limits
            values = [{"role_id": role.id, "router_id": limit.router, "type": limit.type, "value": limit.value} for limit in limits]
            if values:
                await postgres_session.execute(statement=insert(table=LimitTable).values(values))

        if permissions is not None:
            # delete the existing permissions
            await postgres_session.execute(statement=delete(table=PermissionTable).where(PermissionTable.role_id == role.id))

            # Only insert if there are permissions to insert
            if permissions:
                values = [{"role_id": role.id, "permission": permission} for permission in set(permissions)]
                if values:
                    await postgres_session.execute(statement=insert(table=PermissionTable).values(values))

        await postgres_session.commit()

    async def get_roles(
        self,
        postgres_session: AsyncSession,
        role_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created", "updated"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Role]:
        if role_id is None:
            # get the unique role IDs with pagination
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit).order_by(text(f"{order_by} {order_direction}"))
            result = await postgres_session.execute(statement=statement)
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

        result = await postgres_session.execute(role_query)
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

            result = await postgres_session.execute(limits_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].limits.append(Limit(router=row.router_id, type=row.type, value=row.value))

            # Query permissions for these roles
            permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(list(roles.keys())))

            result = await postgres_session.execute(permissions_query)
            for row in result:
                role_id = row.role_id
                if role_id in roles:
                    roles[role_id].permissions.append(PermissionType(value=row.permission))

        return list(roles.values())

    async def create_user(
        self,
        postgres_session: AsyncSession,
        email: str,
        role_id: int,
        name: str | None = None,
        password: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: int | None = None,
        priority: int = 0,
    ) -> int:
        if email == "master":
            raise ReservedEmailException()

        expires = func.to_timestamp(expires) if expires is not None else None

        # check if role exists
        result = await postgres_session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # check if organization exists
        if organization_id is not None:
            result = await postgres_session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise OrganizationNotFoundException()

        password = self._hash_password(password=password) if password is not None else None

        # create the user
        try:
            result = await postgres_session.execute(
                statement=insert(table=UserTable)
                .values(
                    email=email,
                    name=name,
                    password=password,
                    sub=sub,
                    iss=iss,
                    role_id=role_id,
                    organization_id=organization_id,
                    budget=budget,
                    expires=expires,
                    priority=priority,
                )
                .returning(UserTable.id)
            )
            user_id = result.scalar_one()
        except IntegrityError:
            raise UserAlreadyExistsException()

        await postgres_session.commit()

        return user_id

    async def delete_user(self, postgres_session: AsyncSession, user_id: int) -> None:
        # check if user exists
        result = await postgres_session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # delete the user
        await postgres_session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
        await postgres_session.commit()

    async def update_user(
        self,
        postgres_session: AsyncSession,
        user_id: int,
        email: str | None = None,
        name: str | None = None,
        current_password: str | None = None,
        password: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        role_id: int | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: int | None = None,
        priority: int | None = None,
    ) -> None:
        # check if user exists
        result = await postgres_session.execute(
            statement=select(
                UserTable.id,
                UserTable.email,
                UserTable.password,
                UserTable.sub,
                UserTable.iss,
                UserTable.name,
                UserTable.role_id,
                UserTable.budget,
                UserTable.expires,
                UserTable.priority,
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
        email = email if email is not None else user.email

        if email == "master":
            raise ReservedEmailException()

        name = name if name is not None else user.name
        iss = iss if iss is not None else user.iss
        sub = sub if sub is not None else user.sub
        expires = func.to_timestamp(expires) if expires is not None else None
        new_priority = priority if priority is not None else user.priority

        if role_id is not None and role_id != user.role_id:
            # check if role exists
            result = await postgres_session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()
        role_id = role_id if role_id is not None else user.role_id

        if organization_id is not None:
            result = await postgres_session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise OrganizationNotFoundException()

        if password is not None:
            # user has no current password, set new current password without checking if specified current password is correct
            if current_password is None:
                password = self._hash_password(password=password)

            # user has a current password, check if specified current password is correct
            elif self._check_password(password=current_password, hashed_password=user.password):
                password = self._hash_password(password=password)
            else:
                raise InvalidCurrentPasswordException()
        else:
            password = user.password

        await postgres_session.execute(
            statement=update(table=UserTable)
            .values(
                email=email,
                password=password,
                sub=sub,
                iss=iss,
                name=name,
                role_id=role_id,
                organization_id=organization_id,
                budget=budget,
                expires=expires,
                priority=new_priority,
            )
            .where(UserTable.id == user.id)
        )
        await postgres_session.commit()

    async def get_users(
        self,
        postgres_session: AsyncSession,
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

        result = await postgres_session.execute(statement=statement)
        users = [User(**row._mapping) for row in result.all()]

        if (user_id is not None or email is not None) and len(users) == 0:
            raise UserNotFoundException()

        return users

    async def create_organization(self, postgres_session: AsyncSession, name: str) -> int:
        result = await postgres_session.execute(statement=insert(table=OrganizationTable).values(name=name).returning(OrganizationTable.id))
        organization_id = result.scalar_one()
        await postgres_session.commit()

        return organization_id

    async def delete_organization(self, postgres_session: AsyncSession, organization_id: int) -> None:
        result = await postgres_session.execute(statement=select(OrganizationTable.id).where(OrganizationTable.id == organization_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise OrganizationNotFoundException()

        try:
            await postgres_session.execute(statement=delete(table=OrganizationTable).where(OrganizationTable.id == organization_id))
        except IntegrityError:
            raise DeleteOrganizationWithUsersException()

        await postgres_session.commit()

    async def update_organization(self, postgres_session: AsyncSession, organization_id: int, name: str | None = None) -> None:
        result = await postgres_session.execute(statement=select(OrganizationTable).where(OrganizationTable.id == organization_id))
        try:
            organization = result.scalar_one()
        except NoResultFound:
            raise OrganizationNotFoundException()

        if name is not None:
            await postgres_session.execute(statement=update(table=OrganizationTable).values(name=name).where(OrganizationTable.id == organization.id))
        await postgres_session.commit()

    async def get_organizations(
        self,
        postgres_session: AsyncSession,
        organization_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created", "updated"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Organization]:
        statement = (
            select(
                OrganizationTable.id,
                OrganizationTable.name,
                cast(func.extract("epoch", OrganizationTable.created), Integer).label("created"),
                cast(func.extract("epoch", OrganizationTable.updated), Integer).label("updated"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )

        if organization_id is not None:
            statement = statement.where(OrganizationTable.id == organization_id)

        result = await postgres_session.execute(statement=statement)
        organizations = [Organization(**row._mapping) for row in result.all()]

        if organization_id is not None and len(organizations) == 0:
            raise OrganizationNotFoundException()

        return organizations

    async def create_token(self, postgres_session: AsyncSession, user_id: int, name: str, expires: int | None = None) -> tuple[int, str]:
        if self.key_max_expiration_days:
            if expires is None:
                expires = int(dt.datetime.now(tz=dt.UTC).timestamp()) + self.key_max_expiration_days * 86400
            elif expires > int(dt.datetime.now(tz=dt.UTC).timestamp()) + self.key_max_expiration_days * 86400:
                raise InvalidTokenExpirationException(detail=f"Token expiration timestamp cannot be greater than {self.key_max_expiration_days} days from now.")  # fmt: off

        result = await postgres_session.execute(statement=select(UserTable).where(UserTable.id == user_id))
        try:
            user = result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # create the token
        result = await postgres_session.execute(statement=insert(table=TokenTable).values(user_id=user.id, name=name).returning(TokenTable.id))
        token_id = result.scalar_one()
        await postgres_session.commit()

        # generate the token
        token = self._encode_token(user_id=user.id, token_id=token_id, expires=expires)

        # update the token
        expires = func.to_timestamp(expires) if expires is not None else None
        await postgres_session.execute(
            statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires=expires).where(TokenTable.id == token_id)
        )
        await postgres_session.commit()

        return token_id, token

    async def refresh_token(self, postgres_session: AsyncSession, user_id: int, name: str) -> tuple[int, str]:
        """
        Create a new token with the same name, update Usage table references,
        and delete old tokens with the same name and user_id.

        Args:
            postgres_session(AsyncSession): Database postgres_session
            user_id(int): ID of the user
            name(str): Name of the token to refresh

        Returns:
            Tuple containing the new token_id and token
        """
        # delete old for tokens with the same name and user_id
        query = delete(TokenTable).where(TokenTable.user_id == user_id, TokenTable.name == name)
        await postgres_session.execute(query)
        await postgres_session.commit()

        if self.playground_session_duration is None:
            expires = None
        else:
            expires = int((datetime.now() + timedelta(seconds=self.playground_session_duration)).timestamp())

        # Create a new token
        token_id, token = await self.create_token(postgres_session, user_id, name, expires=expires)

        return token_id, token

    async def delete_token(self, postgres_session: AsyncSession, user_id: int, token_id: int) -> None:
        # check if token exists
        result = await postgres_session.execute(statement=select(TokenTable.id).where(TokenTable.id == token_id).where(TokenTable.user_id == user_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise TokenNotFoundException()

        # delete the token
        await postgres_session.execute(statement=delete(table=TokenTable).where(TokenTable.id == token_id))
        await postgres_session.commit()

    async def delete_tokens(self, postgres_session: AsyncSession, user_id: int, name: str):
        """
        Delete tokens for a specific user, optionally filtered by token name

        Args:
            postgres_session: Database postgres_session
            user_id: ID of the user whose tokens should be deleted
            name: name filter for tokens to delete
        """
        query = delete(TokenTable).where(TokenTable.user_id == user_id).where(TokenTable.name == name)

        await postgres_session.execute(query)
        await postgres_session.commit()

    async def get_tokens(
        self,
        postgres_session: AsyncSession,
        user_id: int | None = None,
        token_id: int | None = None,
        exclude_expired: bool = False,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Token]:
        statement = (
            select(
                TokenTable.id,
                TokenTable.name,
                TokenTable.token,
                TokenTable.user_id.label("user"),
                cast(func.extract("epoch", TokenTable.expires), Integer).label("expires"),
                cast(func.extract("epoch", TokenTable.created), Integer).label("created"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(text=f"{order_by} {order_direction}"))
        )

        if user_id is not None:
            statement = statement.where(TokenTable.user_id == user_id)

        if token_id is not None:
            statement = statement.where(TokenTable.id == token_id)

        if exclude_expired is not None:
            statement = statement.where(or_(TokenTable.expires.is_(None), TokenTable.expires >= func.now()))

        result = await postgres_session.execute(statement=statement)
        tokens = [Token(**row._mapping) for row in result.all()]

        if token_id is not None and len(tokens) == 0:
            raise TokenNotFoundException()

        return tokens

    async def check_token(self, postgres_session: AsyncSession, token: str) -> tuple[int | None, int | None, str | None]:
        try:
            claims = self._decode_token(token=token)
        except JWTError:
            return None, None, None
        except IndexError:  # malformed token (no token prefix)
            return None, None, None

        try:
            tokens = await self.get_tokens(postgres_session, user_id=claims["user_id"], token_id=claims["token_id"], exclude_expired=True, limit=1)
        except TokenNotFoundException:
            return None, None, None

        return claims["user_id"], claims["token_id"], tokens[0].name

    async def invalidate_token(self, postgres_session: AsyncSession, token_id: int, user_id: int) -> None:
        """
        Invalidate a token by setting its expires to the current timestamp

        Args:
            postgres_session: Database postgres_session
            token_id: ID of the token to invalidate
            user_id: ID of the user who owns the token (for security)
        """
        await postgres_session.execute(
            update(TokenTable).where(TokenTable.id == token_id).where(TokenTable.user_id == user_id).values(expires=func.now())
        )
        await postgres_session.commit()

    async def get_user(
        self,
        postgres_session: AsyncSession,
        user_id: int | None = None,
        sub: str | None = None,
        email: str | None = None,
    ) -> User | None:
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
        result = await postgres_session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_info(self, postgres_session: AsyncSession, user_id: int | None = None, email: str | None = None) -> UserInfo:
        assert user_id is not None or email is not None, "user_id or email is required"

        if user_id == 0:  # master user
            routers = await global_context.model_registry.get_routers(router_id=None, name=None, postgres_session=postgres_session)
            user = UserInfo(
                id=0,
                email="master",
                name="master",
                organization=0,
                budget=None,
                permissions=[permission for permission in PermissionType],
                limits=[Limit(router=router.id, type=type, value=None) for router in routers for type in LimitType],
                expires=None,
                created=0,
                updated=0,
                priority=0,
            )
        else:
            users = await self.get_users(postgres_session=postgres_session, user_id=user_id, email=email)
            user = users[0]

            roles = await self.get_roles(postgres_session, role_id=user.role)
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

    async def login(self, postgres_session: AsyncSession, email: str, password: str) -> tuple[int, str]:
        """
        Login a user and return the token ID and the token of the refreshed playground token.
        Raise InvalidCurrentPasswordException (400) if password is incorrect and UserNotFoundException (404) if user not found.

        Args:
            postgres_session(AsyncSession): Database postgres_session
            email(str): User email
            password(str): User password

        Returns:
            Tuple containing the token ID and the token of the refreshed playground token.
        """

        if email == "master" and password == self.master_key:
            return 0, self.master_key

        user = await self.get_user_info(postgres_session=postgres_session, email=email)  # raise UserNotFoundException (404) if user not found
        result = await postgres_session.execute(statement=select(UserTable.password).where(UserTable.id == user.id))
        user_password = result.scalar_one()

        if not self._check_password(password=password, hashed_password=user_password):
            raise InvalidCurrentPasswordException()

        token_id, token = await self.refresh_token(postgres_session, user_id=user.id, name=self.PLAYGROUND_KEY_NAME)

        return token_id, token
