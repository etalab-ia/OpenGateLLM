from abc import ABC, abstractmethod


class BaseLoadBalancingStrategy(ABC):
    @abstractmethod
    async def apply_async_strategy(self, candidates: list[int]) -> int:
        """Return the chosen provider ID among candidates."""
        pass
