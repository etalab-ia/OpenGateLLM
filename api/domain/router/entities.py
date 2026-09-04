from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field

from api.domain import EntitiesPage, UtcDatetime
from api.domain.model.entities import ModelType as RouterType
from api.domain.role.entities import LimitType


class RouterLoadBalancingStrategy(StrEnum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


RouterPage = EntitiesPage["Router"]


class Router(BaseModel):
    id: int
    name: str
    user_id: int
    type: RouterType
    aliases: list[str] | None
    load_balancing_strategy: RouterLoadBalancingStrategy
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: int
    created: UtcDatetime
    updated: UtcDatetime

    def with_name(self, name: str) -> "Router":
        return self.model_copy(update={"name": name})

    def with_type(self, router_type: RouterType) -> "Router":
        return self.model_copy(update={"type": router_type})

    def with_load_balancing_strategy(self, strategy: RouterLoadBalancingStrategy) -> "Router":
        return self.model_copy(update={"load_balancing_strategy": strategy})

    def with_cost_prompt_tokens(self, prompt_tokens: float) -> "Router":
        return self.model_copy(update={"cost_prompt_tokens": prompt_tokens})

    def with_cost_completion_tokens(self, completion_tokens: float) -> "Router":
        return self.model_copy(update={"cost_completion_tokens": completion_tokens})

    def with_aliases(self, aliases: list[str]) -> "Router":
        return self.model_copy(update={"aliases": aliases})

    @property
    def has_no_providers(self) -> bool:
        return self.providers == 0

    @property
    def is_billable(self) -> bool:
        return self.cost_prompt_tokens != 0 or self.cost_completion_tokens != 0


class TpmRateLimitState(BaseModel):
    value: int | None = None
    remaining: int = 0
    reset: int = 0


class TpdRateLimitState(BaseModel):
    value: int | None = None
    remaining: int = 0
    reset: int = 0


class RpmRateLimitState(BaseModel):
    value: int | None = 0
    remaining: int = 0
    reset: int = 0


class RpdRateLimitState(BaseModel):
    value: int | None = 0
    remaining: int = 0
    reset: int = 0


class RouterRateLimitState(BaseModel):
    tpm: Annotated[TpmRateLimitState, Field(default_factory=TpmRateLimitState)]
    tpd: Annotated[TpdRateLimitState, Field(default_factory=TpdRateLimitState)]
    rpm: Annotated[RpmRateLimitState, Field(default_factory=RpmRateLimitState)]
    rpd: Annotated[RpdRateLimitState, Field(default_factory=RpdRateLimitState)]

    def exceeded_limits(self, prompt_tokens: int) -> list[LimitType]:
        # floor at 1 so a zero-token request is still blocked by a value == 0 limit
        token_cost = max(prompt_tokens, 1)
        costs = {LimitType.TPM: token_cost, LimitType.TPD: token_cost, LimitType.RPM: 1, LimitType.RPD: 1}
        return [
            limit.value for limit in LimitType if getattr(self, limit.value).value is not None and getattr(self, limit.value).remaining < costs[limit]
        ]

    @classmethod
    def admin_rate_limit_state(cls) -> "RouterRateLimitState":
        return cls(
            tpm=TpmRateLimitState(value=None),
            tpd=TpdRateLimitState(value=None),
            rpm=RpmRateLimitState(value=None),
            rpd=RpdRateLimitState(value=None),
        )

    @property
    def build_limit_headers(self) -> dict[str, str]:
        def seconds_until_reset(reset_epoch: float) -> int:
            return max(0, int(reset_epoch - datetime.now(UTC).timestamp()))

        def format_duration(seconds: int) -> str:
            minutes, secs = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                return f"{hours}h{minutes}m{secs}s"

            if minutes:
                return f"{minutes}m{secs}s"

            return f"{secs}s"

        headers = {}
        if self.tpd.value == 0:
            headers["x-ratelimit-limit-token"] = str(self.tpm.value)
            headers["x-ratelimit-remaining-token"] = str(self.tpm.remaining)
            headers["x-ratelimit-reset-token"] = format_duration(seconds_until_reset(self.tpm.reset))
        else:
            headers["x-ratelimit-limit-token"] = str(self.tpd.value)
            headers["x-ratelimit-remaining-token"] = str(self.tpd.remaining)
            headers["x-ratelimit-reset-token"] = format_duration(seconds_until_reset(self.tpd.reset))

        if self.rpm.value == 0:
            headers["x-ratelimit-limit-request"] = str(self.rpm.value)
            headers["x-ratelimit-remaining-request"] = str(self.rpm.remaining)
            headers["x-ratelimit-reset-requests"] = format_duration(seconds_until_reset(self.rpm.reset))
        else:
            headers["x-ratelimit-limit-request"] = str(self.rpm.value)
            headers["x-ratelimit-remaining-request"] = str(self.rpm.remaining)
            headers["x-ratelimit-reset-requests"] = format_duration(seconds_until_reset(self.rpm.reset))

        return headers
