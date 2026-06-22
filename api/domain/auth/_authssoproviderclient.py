from abc import ABC, abstractmethod

from api.domain.auth.errors import SsoProviderNotAvailableError


class AuthSsoProviderClient(ABC):
    @abstractmethod
    async def get_jwks(self, issuer_url: str) -> dict | SsoProviderNotAvailableError:
        pass
