from dataclasses import dataclass
import time

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository, UserWithRoleQuery
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserExpiredError, UserIsNotAdminError


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


type CreateUserUseCaseResult = (
    CreateUserUseCaseSuccess | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError | UserExpiredError | UserIsNotAdminError
)


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository, user_with_role_query: UserWithRoleQuery):
        self.user_repository = user_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: CreateUserCommand) -> CreateUserUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        if not user.is_admin:
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
