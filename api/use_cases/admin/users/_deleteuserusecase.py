from dataclasses import dataclass

from api.domain.user import UserAuthorization, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserCannotDeleteUserError, UserHasProvidersError, UserHasRoutersError, UserNotFoundError


@dataclass
class DeleteUserCommand:
    authenticated_user_id: int
    user_id: int


@dataclass
class DeleteUserUseCaseSuccess:
    user: User


type DeleteUserUseCaseResult = DeleteUserUseCaseSuccess | UserNotFoundError | UserHasRoutersError | UserHasProvidersError | UserCannotDeleteUserError


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository, user_authorization: UserAuthorization):
        self.user_repository = user_repository
        self.user_authorization = user_authorization

    async def execute(self, command: DeleteUserCommand) -> DeleteUserUseCaseResult:
        is_authorized = await self.user_authorization.can_delete_user(user_id=command.authenticated_user_id, target_user_id=command.user_id)

        if not is_authorized:
            return UserCannotDeleteUserError(user_id=command.authenticated_user_id)

        result = await self.user_repository.delete_user(user_id=command.user_id)

        match result:
            case User() as user:
                await self.user_authorization.detach_admin_from_platform(user_id=user.id)
                return DeleteUserUseCaseSuccess(user=user)
            case UserHasRoutersError() as error:
                return error
            case UserHasProvidersError() as error:
                return error
            case UserNotFoundError(id=user_id):
                return UserNotFoundError(id=user_id)
