from dataclasses import dataclass

from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.userinfo import UserInfoRepository
from api.domain.userinfo.errors import UserIsNotAdminError


@dataclass
class CreateRoleCommand:
    user_id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class CreateRoleUseCaseSuccess:
    role: Role


type CreateRoleUseCaseResult = CreateRoleUseCaseSuccess | RoleAlreadyExistsError | UserIsNotAdminError


class CreateRoleUseCase:
    def __init__(self, role_repository: RoleRepository, user_info_repository: UserInfoRepository):
        self.role_repository = role_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: CreateRoleCommand,
    ) -> CreateRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        result = await self.role_repository.create_role(
            name=command.name,
            permissions=command.permissions,
            limits=command.limits,
        )

        match result:
            case Role() as role:
                return CreateRoleUseCaseSuccess(role)
            case error:
                return error
