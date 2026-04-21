from dataclasses import dataclass

from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import OrganizationNotFoundError, UserAlreadyExistsError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class CreateUserCommand:
    user_id: int
    email: str
    password: str
    role_id: int
    name: str | None = None
    organization_id: int | None = None
    budget: float | None = None
    expires: int | None = None
    priority: int = 0


@dataclass
class CreateUserUseCaseSuccess:
    user: User


type CreateUserUseCaseResult = CreateUserUseCaseSuccess | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError | UserIsNotAdminError


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository, user_info_repository: UserInfoRepository):
        self.user_repository = user_repository
        self.user_info_repository = user_info_repository

    async def execute(self, command: CreateUserCommand) -> CreateUserUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        result = await self.user_repository.create_user(
            email=command.email,
            password=command.password,
            role_id=command.role_id,
            name=command.name,
            organization_id=command.organization_id,
            budget=command.budget,
            expires=command.expires,
            priority=command.priority,
        )

        match result:
            case User() as user:
                return CreateUserUseCaseSuccess(user)
            case error:
                return error
