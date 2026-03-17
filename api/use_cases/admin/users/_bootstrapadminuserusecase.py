from dataclasses import dataclass

from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError


@dataclass
class BootstrapAdminUserCommand:
    email: str
    password: str
    role_id: int
    name: str | None = None


@dataclass
class BootstrapAdminUserUseCaseSuccess:
    user: User


type BootstrapAdminUserUseCaseResult = BootstrapAdminUserUseCaseSuccess | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError


class BootstrapAdminUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, command: BootstrapAdminUserCommand) -> BootstrapAdminUserUseCaseResult:
        result = await self.user_repository.create_user(
            email=command.email,
            password=command.password,
            role_id=command.role_id,
            name=command.name,
        )

        match result:
            case User() as user:
                return BootstrapAdminUserUseCaseSuccess(user)
            case error:
                return error
