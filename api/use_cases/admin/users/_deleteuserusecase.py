from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.router import RouterRepository
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import DeleteUserWithProvidersError, DeleteUserWithRoutersError, UserNotFoundError


@dataclass
class DeleteUserCommand:
    user_id: int


@dataclass
class DeleteUserUseCaseSuccess:
    user: User


type DeleteUserUseCaseResult = DeleteUserUseCaseSuccess | UserNotFoundError | DeleteUserWithRoutersError | DeleteUserWithProvidersError


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository, provider_repository: ProviderRepository, router_repository: RouterRepository):
        self.user_repository = user_repository

        self.provider_repository = provider_repository
        self.router_repository = router_repository

    async def execute(self, command: DeleteUserCommand) -> DeleteUserUseCaseResult:
        result = await self.user_repository.delete_user(user_id=command.user_id)

        match result:
            case User() as user:
                return DeleteUserUseCaseSuccess(user)
            case DeleteUserWithRoutersError():
                router_ids = await self.router_repository.get_router_ids_by_user_id(user_id=command.user_id)
                return DeleteUserWithRoutersError(user_id=command.user_id, router_ids=router_ids)
            case DeleteUserWithProvidersError():
                provider_ids = await self.provider_repository.get_provider_ids_by_user_id(user_id=command.user_id)
                return DeleteUserWithProvidersError(user_id=command.user_id, provider_ids=provider_ids)
            case error:
                return error
