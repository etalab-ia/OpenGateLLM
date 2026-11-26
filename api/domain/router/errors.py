from dataclasses import dataclass

from api.domain import RouterType
from api.domain.role.entities import LimitType


@dataclass
class RouterAliasAlreadyExistsError:
    aliases: list[str]


@dataclass
class RouterNameAlreadyExistsError:
    name: str


@dataclass
class RouterNotFoundError:
    id: int | None = None
    name: str | None = None


@dataclass
class RouterHasNoProvidersError:
    id: int


@dataclass
class RouterHasWrongTypeError:
    id: int
    actual_type: RouterType
    expected_type: RouterType


@dataclass
class UserCannotCreateRouterError:
    user_id: int


@dataclass
class UserCannotDeleteRouterError:
    user_id: int


@dataclass
class RouterRateLimitExceededError:
    id: int
    limit_type: LimitType
    headers: dict[str, str]
