from dataclasses import dataclass


@dataclass
class UserAlreadyExistsError:
    email: str


@dataclass
class RoleNotFoundError:
    role_id: int


@dataclass
class OrganizationNotFoundError:
    organization_id: int
