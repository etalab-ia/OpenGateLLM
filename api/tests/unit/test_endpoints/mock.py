from api.schemas.admin.organizations import Organization
from api.schemas.admin.roles import Limit, LimitType, PermissionType, Role
from api.schemas.admin.tokens import Token
from api.schemas.admin.users import User
from api.schemas.me.info import UserInfo
from api.utils.exceptions import (
    InvalidCurrentPasswordException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)


class MockIdentityAccessManagerSuccess:
    HEADERS = {"Authorization": "Bearer sk-test-api-key"}
    master_key = "sk-test-api-key"

    # roles
    CREATE_ROLE_ID = 1
    GET_ROLE_ID = 2
    GET_ROLE_NAME = "test_role"
    GET_ROLE_PERMISSIONS = [PermissionType.ADMIN.value]
    GET_ROLE_LIMITS = [Limit(router=1, type=LimitType.TPM, value=100)]
    GET_ROLE_USERS = 10
    GET_ROLE_CREATED_AT = 1202932932
    GET_ROLE_UPDATED_AT = 1202932932

    # users
    CREATE_USER_ID = 3
    GET_USER_ID = 4
    GET_USER_EMAIL = "user@example.com"
    GET_USER_NAME = "test_user"
    GET_USER_SUB = None
    GET_USER_ISS = None
    GET_USER_ROLE = 1
    GET_USER_ORGANIZATION = None
    GET_USER_BUDGET = 10000
    GET_USER_EXPIRES_AT = 1202932932
    GET_USER_CREATED_AT = 1202932932
    GET_USER_UPDATED_AT = 1202932932

    # tokens
    CREATE_TOKEN_ID = 5
    CREATE_ORG_ID = 6

    # login
    LOGIN_KEY_ID = 1
    LOGIN_KEY = "sk-test-api-key"

    async def create_role(self, postgres_session, name, permissions, limits) -> int:
        return self.CREATE_ROLE_ID

    async def update_role(self, postgres_session, role_id, name=None, permissions=None, limits=None):
        return None

    async def delete_role(self, postgres_session, role_id):
        return None

    async def get_roles(self, postgres_session, role_id) -> list[Role]:
        return [
            Role(
                id=self.GET_ROLE_ID,
                name=self.GET_ROLE_NAME,
                permissions=self.GET_ROLE_PERMISSIONS,
                limits=self.GET_ROLE_LIMITS,
                users=self.GET_ROLE_USERS,
                created=self.GET_ROLE_CREATED_AT,
                updated=self.GET_ROLE_UPDATED_AT,
            )
        ]

    async def login(self, postgres_session, email, password) -> tuple[int, str]:
        return self.LOGIN_KEY_ID, self.LOGIN_KEY

    async def check_token(self, postgres_session, token):
        return 1, 1

    async def get_user_info(self, postgres_session, user_id=None, email=None) -> UserInfo:
        return UserInfo(
            id=self.CREATE_USER_ID,
            email=self.GET_USER_EMAIL,
            name=self.GET_USER_NAME,
            organization=self.GET_USER_ORGANIZATION,
            budget=self.GET_USER_BUDGET,
            permissions=[PermissionType.ADMIN],
            limits=self.GET_ROLE_LIMITS,
            expires=self.GET_USER_EXPIRES_AT,
            created=self.GET_USER_CREATED_AT,
            updated=self.GET_USER_UPDATED_AT,
        )

    # users
    async def create_user(self, postgres_session, email, password, name, role_id, organization_id, budget, expires) -> int:
        return self.CREATE_USER_ID

    async def update_user(
        self,
        postgres_session,
        user_id,
        email=None,
        name=None,
        current_password=None,
        password=None,
        role_id=None,
        organization_id=None,
        budget=None,
        expires=None,
    ):
        return None

    async def delete_user(self, postgres_session, user_id):
        return None

    async def get_users(
        self, postgres_session, user_id=None, role_id=None, organization_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[User]:
        return [
            User(
                id=self.CREATE_USER_ID,
                email=self.GET_USER_EMAIL,
                name=self.GET_USER_NAME,
                sub=self.GET_USER_SUB,
                iss=self.GET_USER_ISS,
                role=self.GET_USER_ROLE,
                organization=self.GET_USER_ORGANIZATION,
                budget=self.GET_USER_BUDGET,
                expires=self.GET_USER_EXPIRES_AT,
                created=self.GET_USER_CREATED_AT,
                updated=self.GET_USER_UPDATED_AT,
            )
        ]

    # tokens
    async def create_token(self, postgres_session, user_id, name, expires) -> tuple[int, str]:
        return self.CREATE_TOKEN_ID, "token-string"

    async def delete_token(self, postgres_session, user_id, token_id):
        return None

    async def get_tokens(
        self, postgres_session, token_id=None, user_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[Token]:
        return [
            Token(
                id=self.CREATE_TOKEN_ID,
                name="t",
                token="token-string",
                user=self.CREATE_USER_ID,
                expires=None,
                created=0,
            )
        ]

    # organizations
    async def create_organization(self, postgres_session, name) -> int:
        return self.CREATE_ORG_ID

    async def update_organization(self, postgres_session, organization_id, name):
        return None

    async def delete_organization(self, postgres_session, organization_id):
        return None

    async def get_organizations(
        self, postgres_session, organization_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[Organization]:
        return [Organization(id=self.CREATE_ORG_ID, name="org", created=0, updated=0)]


class MockIdentityAccessManagerFail:
    HEADERS = {"Authorization": "Bearer sk-test-api-key"}
    master_key = "sk-test-api-key"

    async def create_role(self, postgres_session, name, permissions, limits) -> int:
        raise RoleAlreadyExistsException()

    async def update_role(self, postgres_session, role_id, name=None, permissions=None, limits=None):
        raise RoleNotFoundException()

    async def delete_role(self, postgres_session, role_id):
        raise RoleNotFoundException()

    async def get_roles(self, postgres_session, role_id) -> list[Role]:
        raise RoleNotFoundException()

    async def login(self, postgres_session, email, password):
        raise InvalidCurrentPasswordException()

    async def check_token(self, postgres_session, token):
        return 1, 1

    async def get_user_info(self, postgres_session, user_id=None, email=None) -> UserInfo:
        return UserInfo(
            id=1,
            email="user@example.com",
            name="user",
            organization=None,
            budget=None,
            permissions=[PermissionType.ADMIN],
            limits=[Limit(router=1, type=LimitType.TPM, value=100)],
            expires=None,
            created=0,
            updated=0,
        )

    # users
    async def create_user(self, postgres_session, email, password, name, role_id, organization_id, budget, expires) -> int:
        raise UserAlreadyExistsException()

    async def update_user(
        self,
        postgres_session,
        user_id,
        email=None,
        name=None,
        current_password=None,
        password=None,
        role_id=None,
        organization_id=None,
        budget=None,
        expires=None,
    ):
        raise UserNotFoundException()

    async def delete_user(self, postgres_session, user_id):
        raise UserNotFoundException()

    async def get_users(
        self, postgres_session, user_id=None, role_id=None, organization_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[User]:
        raise UserNotFoundException()

    # tokens
    async def create_token(self, postgres_session, user_id, name, expires) -> tuple[int, str]:
        raise UserNotFoundException()

    async def delete_token(self, postgres_session, user_id, token_id):
        raise TokenNotFoundException()

    async def get_tokens(
        self, postgres_session, token_id=None, user_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[Token]:
        raise TokenNotFoundException()

    # organizations
    async def create_organization(self, postgres_session, name) -> int:
        raise RoleNotFoundException()

    async def update_organization(self, postgres_session, organization_id, name):
        raise RoleNotFoundException()

    async def delete_organization(self, postgres_session, organization_id):
        raise RoleNotFoundException()

    async def get_organizations(
        self, postgres_session, organization_id=None, offset=0, limit=10, order_by="id", order_direction="asc"
    ) -> list[Organization]:
        raise RoleNotFoundException()
