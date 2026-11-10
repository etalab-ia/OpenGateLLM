from dataclasses import dataclass


@dataclass
class UserHasProvidersError:
    id: int


@dataclass
class UserHasRoutersError:
    id: int


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


@dataclass
class UserCannotCreateUserError:
    user_id: int


@dataclass
class UserCannotDeleteUserError:
    user_id: int


@dataclass
class UserCannotReadUsersError:
    user_id: int


@dataclass
class UserCannotReadUserError:
    user_id: int


@dataclass
class UserCannotUpdateUserError:
    user_id: int
