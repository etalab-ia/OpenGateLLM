from abc import ABC, abstractmethod
from typing import Literal

from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.entities import User
from api.domain.user.errors import UserAlreadyExistsError, UserNotFoundError


class UserRepository(ABC):
    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        role_id: int,
        name: str | None = None,
        sub: str | None = None,
        iss: str | None = None,
        organization_id: int | None = None,
        budget: float | None = None,
        expires: int | None = None,
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
    async def get_users(
        self,
        email: str | None = None,
        user_id: int | None = None,
        role_id: int | None = None,
        organization_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "email", "created", "updated"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[User]:
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User | UserNotFoundError | UserAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> User | UserNotFoundError:
        pass
