from abc import ABC, abstractmethod

from api.domain.auth.errors import SsoInvalidSessionError, SsoProviderNotAvailableError


class AuthSsoSessionValidator(ABC):
    @abstractmethod
    async def validate_session(self, session_cookie: str) -> str | SsoInvalidSessionError | SsoProviderNotAvailableError:
        """
        Validate the session cookie by calling the authentication service and return the email of the user.
        """
        pass
