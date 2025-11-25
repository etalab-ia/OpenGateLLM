from abc import abstractmethod

from pydantic import BaseModel, EmailStr

from api.domain.user.entities import User


class UserRepository(BaseModel):
    @abstractmethod
    async def get_users(self, user_id: int | None = None, email: EmailStr | None = None) -> list[User]:
        pass
