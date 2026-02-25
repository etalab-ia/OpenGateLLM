from abc import ABC, abstractmethod

from api.domain.model import ModelType as RouterType
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterPage, RouterSortField, SortOrder
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError


class RouterRepository(ABC):
    @abstractmethod
    async def get_organization_name(self, user_id) -> str:
        pass

    @abstractmethod
    async def get_all_routers(self) -> list[Router]:
        pass

    @abstractmethod
    async def get_routers_page(
        self,
        limit: int,
        offset: int,
        sort_by: RouterSortField = RouterSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> RouterPage:
        pass

    @abstractmethod
    async def get_router_by_id(self, router_id: int) -> Router | None:
        pass

    @abstractmethod
    async def get_aliases_by_router_id(self, router_id: int) -> list[str]:
        pass

    @abstractmethod
    async def create_router(
        self,
        name: str,
        router_type: RouterType,
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
        aliases: list[str] | None = None,
    ) -> Router | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError:
        pass

    @abstractmethod
    async def delete_router(self, router_id: int) -> Router | None:
        pass
