from abc import ABC, abstractmethod

from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import AuthenticatedUserView


class AuthenticatedUserQuery(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> AuthenticatedUserView | UserNotFoundError:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> AuthenticatedUserView | UserNotFoundError:
        pass
