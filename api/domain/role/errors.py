from dataclasses import dataclass


@dataclass
class RoleAlreadyExistsError:
    name: str


@dataclass
class RoleNotFoundError:
    role_id: int
