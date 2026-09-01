from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from api.domain import SortOrder
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.entities import User, UserPage, UserSortField
from api.domain.user.errors import UserAlreadyExistsError, UserHasProvidersError, UserHasRoutersError, UserNotFoundError


class UserRepository(ABC):
    @abstractmethod
    async def create_user(
        self,
        email: str,
        role_id: int,
        password: str | None = None,
        name: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        claims: dict[str, Any] | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: datetime | None = None,
        priority: int = 0,
    ) -> User | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        pass

    @abstractmethod
    async def get_first_admin_user(self) -> User | UserNotFoundError:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | UserNotFoundError:
        pass

    @abstractmethod
    async def get_user_by_iss_and_sub(self, iss: str, sub: str) -> User | UserNotFoundError:
        pass

    @abstractmethod
    async def get_users(
        self,
        role_id: int | None = None,
        organization_id: int | None = None,
        email: str | None = None,
        offset: int = 0,
        limit: int = 10,
        sort_by: UserSortField = UserSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> UserPage:
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User | UserNotFoundError | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> User | UserNotFoundError | UserHasRoutersError | UserHasProvidersError:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> User | UserNotFoundError:
        pass

    @abstractmethod
    async def get_user_id_and_password_by_email(self, email: str) -> tuple[int, str | None] | UserNotFoundError:
        pass
