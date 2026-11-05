from dataclasses import dataclass


@dataclass
class OrganizationAlreadyExistsError:
    name: str


@dataclass
class OrganizationNotFoundError:
    id: int | None = None
    name: str | None = None


@dataclass
class OrganizationHasUsersError:
    id: int


@dataclass
class UserCannotCreateOrganizationError:
    user_id: int
