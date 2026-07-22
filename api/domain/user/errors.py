from dataclasses import dataclass


@dataclass
class DeleteUserWithProvidersError:
    user_id: int
    provider_ids: list[int] | None


@dataclass
class DeleteUserWithRoutersError:
    user_id: int
    router_ids: list[int] | None


@dataclass
class InvalidUserPasswordError:
    pass


@dataclass
class UserAlreadyExistsError:
    email: str


@dataclass
class UserNotFoundError:
    id: int | None = None
    email: str | None = None


@dataclass
class UserHasInsufficientBudgetError:
    pass


@dataclass
class UserIsNotAdminError:
    pass


@dataclass
class UserExpiredError:
    pass


@dataclass
class UserHasNoAccessToRouterError:
    id: int


@dataclass
class IncorrectCurrentPasswordError:
    user_id: int
