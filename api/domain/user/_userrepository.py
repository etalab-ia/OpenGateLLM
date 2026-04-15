from abc import ABC, abstractmethod
from typing import Literal

from api.domain.user.entities import User
from api.domain.user.errors import OrganizationNotFoundError, RoleNotFoundError, UserAlreadyExistsError


class UserRepository(ABC):
    @abstractmethod
    async def has_admin_user(self) -> bool:
        pass

    @abstractmethod
    async def create_user(
        self,
        email: str,
        role_id: int,
        password: str | None = None,
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
    async def update_user(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> None:
        pass
