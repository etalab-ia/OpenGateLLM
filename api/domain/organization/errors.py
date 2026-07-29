from dataclasses import dataclass


@dataclass
class OrganizationAlreadyExistsError:
    name: str


@dataclass
class OrganizationNotFoundError:
    id: int | None = None
    name: str | None = None
