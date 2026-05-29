from dataclasses import dataclass

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError


@dataclass
class CreateRoleCommand:
    user_id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class CreateRoleUseCaseSuccess:
    role: Role


type CreateRoleUseCaseResult = CreateRoleUseCaseSuccess | RoleAlreadyExistsError | UserExpiredError | UserIsNotAdminError


class CreateRoleUseCase:
    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        user_with_role_query: UserWithRoleQuery,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: CreateRoleCommand) -> CreateRoleUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)

        if user.has_expired:
            return UserExpiredError()

        if not user.is_admin:
            return UserIsNotAdminError()

        result = await self.role_repository.create_role(name=command.name)
        match result:
            case Role() as created_role:
                role = created_role
            case error:
                return error
        permissions = await self.permission_repository.create_permissions(role_id=role.id, permissions=command.permissions)
        limits = await self.limit_repository.create_limits(role_id=role.id, limits=command.limits)
        return CreateRoleUseCaseSuccess(role=role.model_copy(update={"permissions": permissions, "limits": limits}))
