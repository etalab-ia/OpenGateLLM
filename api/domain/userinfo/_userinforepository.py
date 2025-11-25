from abc import ABC, abstractmethod

from api.domain.userinfo.entities import UserInfo


class UserInfoRepository(ABC):
    @abstractmethod
    def get_user_info(self, user_id: int | None = None, email: str | None = None) -> UserInfo:
        pass
