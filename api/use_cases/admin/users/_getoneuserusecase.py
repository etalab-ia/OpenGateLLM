from dataclasses import dataclass

from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserCannotReadUserError, UserNotFoundError


@dataclass
class GetOneUserCommand:
    authenticated_user_id: int
    user_id: int


@dataclass
class GetOneUserUseCaseSuccess:
    user: User


type GetOneUserUseCaseResult = GetOneUserUseCaseSuccess | UserNotFoundError | UserCannotReadUserError


class GetOneUserUseCase:
    def __init__(self, user_repository: UserRepository, user_authorization: UserAuthorization):
        self.user_repository = user_repository
        self.user_authorization = user_authorization

    async def execute(self, command: GetOneUserCommand) -> GetOneUserUseCaseResult:
        is_authorized = await self.user_authorization.can_read_user(user_id=command.authenticated_user_id, target_user_id=command.user_id)

        if not is_authorized:
            return UserCannotReadUserError(user_id=command.authenticated_user_id)

        result = await self.user_repository.get_user_by_id(user_id=command.user_id)

        match result:
            case User() as user:
                return GetOneUserUseCaseSuccess(user)
            case error:
                return error
