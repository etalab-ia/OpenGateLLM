from abc import ABC, abstractmethod

from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy


class RouterRepository(ABC):
    @abstractmethod
    async def get_organization_name(self, user_id) -> str:
        pass

    @abstractmethod
    async def get_all_routers(self) -> list[Router]:
        pass

    @abstractmethod
    async def create_router(
        self,
        name: str,
        type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: str,
    ) -> list[Router]:
        pass
