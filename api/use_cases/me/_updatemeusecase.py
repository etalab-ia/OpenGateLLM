from dataclasses import dataclass

from pydantic import SecretStr

from api.domain.user import UserPasswordEncoder, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError


@dataclass
class UpdateMeCommand:
    user_id: int
    email: str
    name: str
    current_password: str | None = None
    new_password: str | None = None


@dataclass
class UpdateMeUseCaseSuccess:
    user: User


type UpdateMeUseCaseResult = UpdateMeUseCaseSuccess | UserNotFoundError | UserAlreadyExistsError | IncorrectCurrentPasswordError


class UpdateMeUseCase:
    def __init__(self, user_repository: UserRepository, user_password_encoder: UserPasswordEncoder):
        self.user_repository = user_repository
        self.user_password_encoder = user_password_encoder

    async def execute(self, command: UpdateMeCommand) -> UpdateMeUseCaseResult:
        existing_user = await self.user_repository.get_user_by_id(user_id=command.user_id)
        if isinstance(existing_user, UserNotFoundError):
            return existing_user

        if command.current_password is None or command.new_password is None:
            password = existing_user.password

        elif existing_user.password is None or self.user_password_encoder.validate_password(
            password=command.current_password,
            encoded_password=existing_user.password.get_secret_value(),
        ):
            password = SecretStr(self.user_password_encoder.encode_password(password=command.new_password))
        else:
            return IncorrectCurrentPasswordError(user_id=existing_user.id)

        updated_user = existing_user.model_copy(
            update={
                "email": command.email,
                "name": command.name,
                "password": password,
            }
        )

        result = await self.user_repository.update_user(user=updated_user)

        match result:
            case User() as user:
                return UpdateMeUseCaseSuccess(user)
            case error:
                return error
