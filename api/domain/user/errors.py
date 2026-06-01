from dataclasses import dataclass


@dataclass
class UserAlreadyExistsError:
    email: str


@dataclass
class UserNotFoundError:
    id: int | None = None
    email: str | None = None


@dataclass
class UserIsNotAdminError:
    pass


@dataclass
class UserExpiredError:
    pass


@dataclass
class DeleteUserWithProvidersError:
    user_id: int
    providers_ids: list[int] | None


@dataclass
class DeleteUserWithRoutersError:
    user_id: int
    routers_ids: list[int] | None
