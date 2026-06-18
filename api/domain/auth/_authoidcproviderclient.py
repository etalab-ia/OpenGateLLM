from abc import ABC, abstractmethod

from api.domain.auth.errors import OidcProviderNotAvailableError


class AuthOidcProviderClient(ABC):
    @abstractmethod
    async def get_jwks(self, issuer_url: str) -> dict | OidcProviderNotAvailableError:
        pass
