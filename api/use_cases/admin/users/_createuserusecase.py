from dataclasses import dataclass

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserPasswordEncoder, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError


@dataclass
class CreateUserCommand:
    email: str
    role_id: int
    password: str | None = None
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
    def __init__(self, user_repository: UserRepository, user_password_encoder: UserPasswordEncoder):
        self.user_repository = user_repository
        self.user_password_encoder = user_password_encoder

    async def execute(self, command: CreateUserCommand) -> CreateUserUseCaseResult:
        password = self.user_password_encoder.encode_password(password=command.password) if command.password is not None else None
        result = await self.user_repository.create_user(
            email=command.email,
            password=password,
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
