from abc import ABC, abstractmethod

from api.domain.model import Model
from api.domain.userinfo import UserInfo


class ModelRepository(ABC):
    @abstractmethod
    def get_all_models(self, name: str | None, user_info: UserInfo) -> list[Model]:
        pass
