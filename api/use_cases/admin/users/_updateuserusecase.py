from dataclasses import dataclass

from pydantic import SecretStr

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserPasswordEncoder, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError


@dataclass
class UpdateUserCommand:
    user_id: int
    email: str | None = None
    name: str | None = None
    current_password: str | None = None
    new_password: str | None = None
    role_id: int | None = None
    organization_id: int | None = None
    budget: float | None = None
    expires: int | None = None
    priority: int | None = None


@dataclass
class UpdateUserUseCaseSuccess:
    user: User


type UpdateUserUseCaseResult = (
    UpdateUserUseCaseSuccess
    | UserNotFoundError
    | UserAlreadyExistsError
    | RoleNotFoundError
    | OrganizationNotFoundError
    | IncorrectCurrentPasswordError
)


class UpdateUserUseCase:
    def __init__(self, user_repository: UserRepository, user_password_encoder: UserPasswordEncoder):
        self.user_repository = user_repository
        self.user_password_encoder = user_password_encoder

    async def execute(self, command: UpdateUserCommand) -> UpdateUserUseCaseResult:
        existing_user = await self.user_repository.get_user_by_id(user_id=command.user_id)
        if isinstance(existing_user, UserNotFoundError):
            return existing_user

        if command.new_password is None:
            password = existing_user.password
        elif command.current_password is None:
            password = SecretStr(self.user_password_encoder.encode_password(password=command.new_password))
        elif existing_user.password is not None and self.user_password_encoder.validate_password(
            password=command.current_password, encoded_password=existing_user.password.get_secret_value()
        ):
            password = SecretStr(self.user_password_encoder.encode_password(password=command.new_password))
        else:
            return IncorrectCurrentPasswordError(user_id=existing_user.id)

        updated_user = existing_user.model_copy(
            update={
                "email": command.email if command.email is not None else existing_user.email,
                "role_id": command.role_id if command.role_id is not None else existing_user.role_id,
                "priority": command.priority if command.priority is not None else existing_user.priority,
                "name": command.name,
                "organization_id": command.organization_id,
                "budget": command.budget,
                "expires": command.expires,
                "password": password,
            }
        )

        result = await self.user_repository.update_user(user=updated_user)

        match result:
            case User() as user:
                return UpdateUserUseCaseSuccess(user)
            case error:
                return error
