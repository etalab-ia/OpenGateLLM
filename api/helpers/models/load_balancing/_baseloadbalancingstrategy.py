from abc import ABC, abstractmethod


class BaseLoadBalancingStrategy(ABC):
    @abstractmethod
    def apply_sync_strategy(self, candidates: list[int]) -> tuple[int, float | None]:
        """
        Apply the sync load balancing strategy to the candidates.

        Args:
            candidates (list[int]): The list of provider candidates (provider IDs) to choose from

        Returns:
           tuple[int, float | None]: The chosen provider ID and its performance indicator
        """
        pass

    @abstractmethod
    async def apply_async_strategy(self, candidates: list[int]) -> tuple[int, float | None]:
        """
        Apply the async load balancing strategy to the candidates.

        Args:
            candidates (list[int]): The list of provider candidates (provider IDs) to choose from

        Returns:
            tuple[int, float | None]: The chosen provider ID and its performance indicator
        """
        pass
