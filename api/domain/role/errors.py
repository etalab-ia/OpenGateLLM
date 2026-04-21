from dataclasses import dataclass


@dataclass
class RoleAlreadyExistsError:
    name: str


@dataclass
class RoleNotFoundError:
    role_id: int


@dataclass
class RoleHasUsersError:
    role_id: int
    number_of_users: int
