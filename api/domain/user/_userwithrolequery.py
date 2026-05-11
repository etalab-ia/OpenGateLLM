from abc import ABC, abstractmethod

from api.domain.user.views import UserWithRoleView
from api.utils.exceptions import UserNotFoundException


class UserWithRoleQuery(ABC):
    @abstractmethod
    async def get_user_with_role_by_id(self, user_id: int) -> UserWithRoleView | UserNotFoundException:
        pass

    @abstractmethod
    async def get_user_with_role_by_email(self, email: str) -> UserWithRoleView | UserNotFoundException:
        pass
