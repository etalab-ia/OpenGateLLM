import random

from api.helpers.load_balancing import BaseLoadBalancingStrategy


class ShuffleLoadBalancingStrategy(BaseLoadBalancingStrategy):
    def apply_sync_strategy(self, candidates: list[int]) -> tuple[int, None]:
        return random.choice(candidates), None

    async def apply_async_strategy(self, candidates: list[int]) -> tuple[int, None]:
        return random.choice(candidates), None
