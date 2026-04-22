from dataclasses import dataclass


@dataclass
class UserAlreadyExistsError:
    email: str


@dataclass
class OrganizationNotFoundError:
    id: int
