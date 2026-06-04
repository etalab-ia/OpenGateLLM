from dataclasses import dataclass

from api.domain.provider import ProviderRepository
from api.domain.router import RouterRepository
from api.domain.user import UserRepository, UserWithRoleQuery
from api.domain.user.entities import User
from api.domain.user.errors import DeleteUserWithProvidersError, DeleteUserWithRoutersError, UserExpiredError, UserIsNotAdminError, UserNotFoundError


@dataclass
class DeleteUserCommand:
    authenticated_user_id: int
    user_id: int


@dataclass
class DeleteUserUseCaseSuccess:
    user: User


type DeleteUserUseCaseResult = (
    DeleteUserUseCaseSuccess | UserExpiredError | UserIsNotAdminError | UserNotFoundError | DeleteUserWithRoutersError | DeleteUserWithProvidersError
)


class DeleteUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        provider_repository: ProviderRepository,
        router_repository: RouterRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.user_repository = user_repository
        self.user_with_role_query = user_with_role_query
        self.provider_repository = provider_repository
        self.router_repository = router_repository

    async def execute(self, command: DeleteUserCommand) -> DeleteUserUseCaseResult:
        authenticated_user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.authenticated_user_id)

        if authenticated_user.has_expired:
            return UserExpiredError()

        if not authenticated_user.is_admin:
            return UserIsNotAdminError()

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
