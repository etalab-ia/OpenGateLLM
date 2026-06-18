from abc import ABC, abstractmethod
from typing import Any

from api.domain.auth.errors import InvalidOidcTokenError


class AuthOidcTokenValidator(ABC):
    @abstractmethod
    async def validate_token(self, id_token: str, client_id: str, jwks: dict) -> dict[str, Any] | InvalidOidcTokenError:
        pass
