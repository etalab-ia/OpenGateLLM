from dataclasses import dataclass


@dataclass
class OrganizationNotFoundError:
    id: int
