from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.auth.errors import InvalidOidcTokenError, SsoProviderNotAvailableError


@dataclass(frozen=True)
class SsoSessionClaims:
    email: str
    user: str | None = None


class AuthSsoSessionValidator(ABC):
    @abstractmethod
    async def validate_session(self, session_cookie: str) -> SsoSessionClaims | InvalidOidcTokenError | SsoProviderNotAvailableError:
        pass
