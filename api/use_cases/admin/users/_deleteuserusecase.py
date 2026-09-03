from dataclasses import dataclass

from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserHasProvidersError, UserHasRoutersError, UserNotFoundError


@dataclass
class DeleteUserCommand:
    user_id: int


@dataclass
class DeleteUserUseCaseSuccess:
    user: User


type DeleteUserUseCaseResult = DeleteUserUseCaseSuccess | UserNotFoundError | UserHasRoutersError | UserHasProvidersError


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, command: DeleteUserCommand) -> DeleteUserUseCaseResult:
        result = await self.user_repository.delete_user(user_id=command.user_id)

        match result:
            case User() as user:
                return DeleteUserUseCaseSuccess(user=user)
            case UserHasRoutersError() as error:
                return error
            case UserHasProvidersError() as error:
                return error
            case UserNotFoundError(id=user_id):
                return UserNotFoundError(id=user_id)
