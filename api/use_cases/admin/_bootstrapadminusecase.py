from dataclasses import dataclass
import logging

from api.domain.role import LimitRepository, PermissionRepository, RoleRepository
from api.domain.role.entities import PermissionType, Role
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.domain.user import UserPasswordEncoder, UserRepository
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class BootstrapAdminCommand:
    email: str
    password: str


@dataclass
class BootstrapAdminUseCaseSuccess:
    user_id: int
    email: str
    role_id: int


@dataclass
class BootstrapAdminUseCaseSkipped:
    user_id: int | None = None
    email: str | None = None
    role_id: int | None = None


type BootstrapAdminUseCaseResult = BootstrapAdminUseCaseSuccess | BootstrapAdminUseCaseSkipped


class BootstrapAdminUseCase:
    BOOTSTRAP_ADMIN_USER_NAME = "bootstrap_admin"
    BOOTSTRAP_ADMIN_ROLE_NAME = "bootstrap_admin"

    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        limit_repository: LimitRepository,
        user_repository: UserRepository,
        user_password_encoder: UserPasswordEncoder,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.limit_repository = limit_repository
        self.user_repository = user_repository
        self.user_password_encoder = user_password_encoder

    async def execute(self, command: BootstrapAdminCommand) -> BootstrapAdminUseCaseResult:
        result = await self.user_repository.get_first_admin_user()
        match result:
            case User() as user:
                return BootstrapAdminUseCaseSkipped(user_id=user.id, email=user.email, role_id=user.role_id)

        result = await self.role_repository.get_role_with_permissions_and_limits_by_name(role_name=self.BOOTSTRAP_ADMIN_ROLE_NAME)
        match result:
            case Role() as role:
                if PermissionType.ADMIN not in role.permissions:
                    await self.permission_repository.create_permissions(role_id=role.id, permissions=[*role.permissions, PermissionType.ADMIN])
            case RoleNotFoundError():
                result = await self.role_repository.create_role(name=self.BOOTSTRAP_ADMIN_ROLE_NAME)
                match result:
                    case Role() as role:
                        await self.permission_repository.create_permissions(role_id=role.id, permissions=[PermissionType.ADMIN])
                    case RoleAlreadyExistsError():
                        return BootstrapAdminUseCaseSkipped()

        result = await self.user_repository.get_user_by_email(email=command.email)
        match result:
            case User() as user:
                if user.role_id != role.id:
                    await self.user_repository.update_user(user=user.model_copy(update={"role_id": role.id}))
            case UserNotFoundError():
                result = await self.user_repository.create_user(
                    email=command.email,
                    password=self.user_password_encoder.encode_password(password=command.password),
                    role_id=role.id,
                    name=self.BOOTSTRAP_ADMIN_USER_NAME,
                )
                match result:
                    case User() as user:
                        pass
                    case UserAlreadyExistsError():
                        return BootstrapAdminUseCaseSkipped()

        return BootstrapAdminUseCaseSuccess(user_id=user.id, email=user.email, role_id=role.id)
