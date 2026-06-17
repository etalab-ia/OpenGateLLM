from abc import ABC, abstractmethod

from api.domain.user.views import AuthenticatedUserView
from api.utils.exceptions import UserNotFoundException


class AuthenticatedUserQuery(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> AuthenticatedUserView | UserNotFoundException:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> AuthenticatedUserView | UserNotFoundException:
        pass
