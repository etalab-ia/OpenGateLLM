from dataclasses import dataclass

from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError


@dataclass
class GetOneUserCommand:
    user_id: int


@dataclass
class GetOneUserUseCaseSuccess:
    user: User


type GetOneUserUseCaseResult = GetOneUserUseCaseSuccess | UserNotFoundError


class GetOneUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, command: GetOneUserCommand) -> GetOneUserUseCaseResult:
        result = await self.user_repository.get_user_by_id(user_id=command.user_id)

        match result:
            case User() as user:
                return GetOneUserUseCaseSuccess(user)
            case error:
                return error
