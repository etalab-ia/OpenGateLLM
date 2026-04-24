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
    number_of_users: int
