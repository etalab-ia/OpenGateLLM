from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleNotFoundError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import UserInfo


@dataclass
class GetUserInfoCommand:
    user_id: int


@dataclass
class GetUserInfoUseCaseSuccess:
    user_info: UserInfo


type GetUserInfoUseCaseResult = GetUserInfoUseCaseSuccess | UserNotFoundError | RoleNotFoundError


class GetUserInfoUseCase:
    def __init__(self, user_repository: UserRepository, role_repository: RoleRepository):
        self.user_repository = user_repository
        self.role_repository = role_repository

    async def execute(self, command: GetUserInfoCommand) -> GetUserInfoUseCaseResult:
        user_result = await self.user_repository.get_user_by_id(user_id=command.user_id)
        match user_result:
            case User() as user:
                pass
            case error:
                return error

        role_result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=user.role_id)
        match role_result:
            case Role() as role:
                pass
            case error:
                return error

        limits = [limit for limit in role.limits if limit.value is None or limit.value > 0]
        user_info = UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            organization_id=user.organization_id,
            budget=user.budget,
            permissions=role.permissions,
            limits=limits,
            expires=user.expires,
            priority=user.priority,
            created=user.created,
            updated=user.updated,
        )
        return GetUserInfoUseCaseSuccess(user_info=user_info)
