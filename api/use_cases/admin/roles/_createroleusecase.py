from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleAuthorization, RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError, UserCannotCreateRoleError


@dataclass
class CreateRoleCommand:
    authenticated_user_id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class CreateRoleUseCaseSuccess:
    role: Role


type CreateRoleUseCaseResult = CreateRoleUseCaseSuccess | RoleAlreadyExistsError | UserCannotCreateRoleError


class CreateRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        role_authorization: RoleAuthorization,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.role_authorization = role_authorization

    async def execute(self, command: CreateRoleCommand) -> CreateRoleUseCaseResult:
        is_authorized = await self.role_authorization.can_create_role(user_id=command.authenticated_user_id)
        if not is_authorized:
            return UserCannotCreateRoleError(user_id=command.authenticated_user_id)

        result = await self.role_repository.create_role(name=command.name)
        match result:
            case Role() as created_role:
                role = created_role
            case error:
                return error
        permissions = await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)
        limits = await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        return CreateRoleUseCaseSuccess(role=role.model_copy(update={"permissions": permissions, "limits": limits}))
