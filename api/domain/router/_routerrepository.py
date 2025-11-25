from abc import ABC, abstractmethod

from api.domain.router.entities import Model, Router
from api.domain.userinfo.entities import UserInfo


class RouterRepository(ABC):
    @abstractmethod
    def get_routers(self, router_id: int | None, name: str | None) -> list[Router]:
        pass

    @abstractmethod
    def get_all_models(self, name: str | None, user_info: UserInfo) -> list[Model]:
        pass
