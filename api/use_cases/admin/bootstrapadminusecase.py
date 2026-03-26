from dataclasses import dataclass
import logging

from api.domain.role import RoleRepository
from api.domain.role.entities import Limit, PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError
from api.domain.user import UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError

logger = logging.getLogger(__name__)


@dataclass
class BootstrapAdminCommand:
    name: str
    email: str
    password: str
    permissions: list[PermissionType]
    limits: list[Limit]


@dataclass
class BootstrapAdminUseCaseSuccess:
    user_id: int
    email: str
    role_id: int


@dataclass
class BootstrapAdminUseCaseSkipped:
    name: str
    email: str


type BootstrapAdminUseCaseResult = BootstrapAdminUseCaseSuccess | BootstrapAdminUseCaseSkipped | RoleAlreadyExistsError | UserAlreadyExistsError


class BootstrapAdminUseCase:
    def __init__(self, role_repository: RoleRepository, user_repository: UserRepository):
        self.role_repository = role_repository
        self.user_repository = user_repository

    async def execute(self, command: BootstrapAdminCommand) -> BootstrapAdminUseCaseResult:
        if await self.user_repository.has_admin_user():
            return BootstrapAdminUseCaseSkipped(name=command.name, email=command.email)

        result = await self.role_repository.create_role(
            name=command.name,
            permissions=command.permissions,
            limits=command.limits,
        )
        match result:
            case Role() as role_result:
                role = role_result
            case error:
                return error

        result = await self.user_repository.create_user(
            email=command.email,
            password=command.password,
            role_id=role.id,
            name=command.name,
        )
        match result:
            case User() as user:
                return BootstrapAdminUseCaseSuccess(
                    user_id=user.id,
                    email=user.email,
                    role_id=role.id,
                )
            case error:
                return error
