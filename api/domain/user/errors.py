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
