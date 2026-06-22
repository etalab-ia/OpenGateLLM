from abc import ABC, abstractmethod
from typing import Any

from api.domain.auth.errors import InvalidOidcTokenError


class AuthSsoTokenValidator(ABC):
    @abstractmethod
    async def validate_token(self, token: str, client_id: str, jwks: dict) -> dict[str, Any] | InvalidOidcTokenError:
        pass
