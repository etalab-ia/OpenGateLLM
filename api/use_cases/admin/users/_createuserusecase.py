from dataclasses import dataclass

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError


@dataclass
class CreateUserCommand:
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


type CreateUserUseCaseResult = CreateUserUseCaseSuccess | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, command: CreateUserCommand) -> CreateUserUseCaseResult:
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
