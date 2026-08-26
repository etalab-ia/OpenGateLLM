from abc import ABC, abstractmethod

from api.domain import SortField, SortOrder
from api.domain.model.entities import ModelType as RouterType
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterPage
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError


class RouterRepository(ABC):
    @abstractmethod
    async def get_all_routers(self) -> list[Router]:
        pass

    @abstractmethod
    async def get_routers_page(
        self,
        limit: int,
        offset: int,
        sort_by: SortField = SortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> RouterPage:
        pass

    @abstractmethod
    async def get_router_by_id(self, router_id: int) -> Router | RouterNotFoundError:
        pass

    @abstractmethod
    async def get_router_by_name_or_alias(self, name_or_alias: str) -> Router | RouterNotFoundError:
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
    async def delete_router(self, router_id: int) -> Router | RouterNotFoundError:
        pass

    @abstractmethod
    async def delete_all_routers(self) -> list[Router]:
        pass

    @abstractmethod
    async def get_aliases(self, filtered_aliases: list[str] | None = None) -> list[str]:
        pass

    @abstractmethod
    async def update_router(self, router: Router) -> Router | RouterNameAlreadyExistsError:
        pass

    @abstractmethod
    async def get_router_ids_by_user_id(self, user_id: int) -> list[int]:
        pass
