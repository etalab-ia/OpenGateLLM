from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
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
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        user_info_repository: UserInfoRepository,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        command: CreateRoleCommand,
    ) -> CreateRoleUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=command.user_id)

        if not user_info.is_admin:
            return UserIsNotAdminError()

        result = await self.role_repository.create_role(name=command.name)
        match result:
            case Role() as created_role:
                role = created_role
            case error:
                return error
        permissions = await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)
        limits = await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        role.permissions = permissions
        role.limits = limits
        return CreateRoleUseCaseSuccess(role)
