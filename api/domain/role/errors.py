from dataclasses import dataclass


@dataclass
class RoleAlreadyExistsError:
    name: str


@dataclass
class RoleNotFoundError:
    id: int


@dataclass
class RoleHasUsersError:
    id: int
    number_of_users: int
