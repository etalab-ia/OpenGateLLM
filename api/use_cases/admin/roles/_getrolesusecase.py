import asyncio
from dataclasses import dataclass, replace

from api.domain import SortField, SortOrder
from api.domain.role import LimitRepository, PermissionRepository, RoleAuthorization, RoleRepository
from api.domain.role.entities import RolePage
from api.domain.role.errors import UserCannotReadRolesError


@dataclass
class GetRolesCommand:
    authenticated_user_id: int
    offset: int = 0
    limit: int = 10
    sort_by: SortField = SortField.ID
    sort_order: SortOrder = SortOrder.ASC


@dataclass
class GetRolesUseCaseSuccess:
    role_page: RolePage


type GetRolesUseCaseResult = GetRolesUseCaseSuccess | UserCannotReadRolesError


class GetRolesUseCase:
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

    async def execute(self, command: GetRolesCommand) -> GetRolesUseCaseResult:
        is_authorized = await self.role_authorization.can_read_roles(user_id=command.authenticated_user_id)
        if not is_authorized:
            return UserCannotReadRolesError(user_id=command.authenticated_user_id)

        role_page = await self.role_repository.get_roles_page(
            limit=command.limit, offset=command.offset, sort_by=command.sort_by, sort_order=command.sort_order
        )

        if role_page.data:
            role_ids = [role.id for role in role_page.data]
            limits, permissions = await asyncio.gather(
                self.limit_repository.get_limits_by_role_ids(role_ids=role_ids),
                self.permission_repository.get_permissions_by_role_ids(role_ids=role_ids),
            )

            full_roles = [role.with_limits(limits.get(role.id, [])).with_permissions(permissions.get(role.id, [])) for role in role_page.data]
            role_page = replace(role_page, data=full_roles)

        return GetRolesUseCaseSuccess(role_page=role_page)
