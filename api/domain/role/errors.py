from dataclasses import dataclass


@dataclass
class RoleAlreadyExistsError:
    name: str


@dataclass
class RoleNotFoundError:
    id: int | None = None
    name: str | None = None


@dataclass
class RoleHasUsersError:
    id: int


@dataclass
class RoleAdminPermissionChangeError:
    id: int


@dataclass
class UserCannotCreateRoleError:
    user_id: int


@dataclass
class UserCannotReadRolesError:
    user_id: int


@dataclass
class UserCannotReadRoleError:
    user_id: int


@dataclass
class UserCannotUpdateRoleError:
    user_id: int


@dataclass
class UserCannotDeleteRoleError:
    user_id: int
