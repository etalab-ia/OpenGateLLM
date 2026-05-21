from dataclasses import dataclass

from api.domain.router.entities import RouterType
from api.schemas.admin.roles import LimitType


@dataclass
class RouterAliasAlreadyExistsError:
    aliases: list[str]


@dataclass
class RouterNameAlreadyExistsError:
    name: str


@dataclass
class RouterNotFoundError:  # TODO: récupérer name dans exception http
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
class RouterRateLimitExceededError:
    id: int
    limit_type: LimitType
    headers: dict[str, str]
