from abc import abstractmethod, ABC
from typing import Any

class UserInfoRepository(ABC):
    @abstractmethod
    def get_user_info(self, user_id: str) -> dict:
        pass

    @abstractmethod
    def update_user_info(self, user_id: str, info: dict) -> None:
        pass