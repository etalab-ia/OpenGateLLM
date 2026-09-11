import random

from ._baseloadbalancingstrategy import BaseLoadBalancingStrategy


class ShuffleLoadBalancingStrategy(BaseLoadBalancingStrategy):
    async def apply_async_strategy(self, candidates: list[int]) -> int:
        return random.choice(candidates)
