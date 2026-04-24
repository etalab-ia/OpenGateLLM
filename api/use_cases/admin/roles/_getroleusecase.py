from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Role
from api.domain.role.errors import RoleNotFoundError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class GetRoleCommand:
    user_id: int
    role_id: int


@dataclass
class GetRoleUseCaseSuccess:
    role: Role


type GetRoleUseCaseResult = GetRoleUseCaseSuccess | RoleNotFoundError | UserIsNotAdminError


class GetRoleUseCase:
    def __init__(self, role_repository: RoleRepository, user_info_repository: UserInfoRepository):
        self.role_repository = role_repository
        self.user_info_repository = user_info_repository

    async def execute(self, command: GetRoleCommand) -> GetRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        result = await self.role_repository.get_role_with_permissions_and_limits_by_id(role_id=command.role_id)
        match result:
            case Role() as role:
                return GetRoleUseCaseSuccess(role=role)
            case RoleNotFoundError():
                return RoleNotFoundError(id=command.role_id)
