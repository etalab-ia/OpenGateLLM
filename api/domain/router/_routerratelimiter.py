from abc import ABC, abstractmethod

from api.domain.role.entities import Limit
from api.domain.router.entities import RouterRateLimitState


class RouterRateLimiter(ABC):
    @abstractmethod
    async def get_rate_limit_state(self, user_id: int, router_limits: list[Limit], router_id: int) -> RouterRateLimitState:
        pass

    @abstractmethod
    async def update_rate_limit_state(
        self, user_id: int, router_limits: list[Limit], router_id: int, prompt_tokens: int, completion_tokens: int
    ) -> None:
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset the rate limit state of all users when the API is restarted."""
        pass
