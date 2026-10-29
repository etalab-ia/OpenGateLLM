from dataclasses import dataclass

from api.domain import UtcDatetime
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role import RoleRepository
from api.domain.role.entities import PermissionType
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserAuthorization, UserPasswordEncoder, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError


@dataclass
class CreateUserCommand:
    email: str
    role_id: int
    organization_id: int
    password: str
    name: str | None = None
    expires: UtcDatetime | None = None
    priority: int = 0


@dataclass
class CreateUserUseCaseSuccess:
    user: User


type CreateUserUseCaseResult = CreateUserUseCaseSuccess | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        user_password_encoder: UserPasswordEncoder,
        user_authorization: UserAuthorization,
    ):
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.user_password_encoder = user_password_encoder
        self.user_authorization = user_authorization

    async def execute(self, command: CreateUserCommand) -> CreateUserUseCaseResult:
        role = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match role:
            case RoleNotFoundError() as error:
                return error

        password = self.user_password_encoder.encode_password(password=command.password)
        result = await self.user_repository.create_user(
            email=command.email,
            password=password,
            role_id=command.role_id,
            name=command.name,
            organization_id=command.organization_id,
            expires=command.expires,
            priority=command.priority,
        )

        match result:
            case User() as user:
                if PermissionType.ADMIN in role.permissions:
                    await self.user_authorization.attach_admin_to_platform(user_id=user.id)
                return CreateUserUseCaseSuccess(user)
            case error:
                return error
