from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

from api.domain import EntitiesPage, UtcDatetime
from api.domain.role.entities import LimitType


class RouterLoadBalancingStrategy(StrEnum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


RouterPage = EntitiesPage["Router"]


class RouterType(StrEnum):
    AUTOMATIC_SPEECH_RECOGNITION = "automatic-speech-recognition"
    IMAGE_TO_TEXT = "image-to-text"
    TEXT_CLASSIFICATION = "text-classification"
    TEXT_EMBEDDINGS_INFERENCE = "text-embeddings-inference"
    TEXT_GENERATION = "text-generation"


class Router(BaseModel):
    id: int
    name: str
    user_id: int
    type: RouterType
    aliases: list[str]
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


class TpmRateLimitState(BaseModel):
    PERIOD_SECONDS: ClassVar[int] = 60

    value: int | None = None
    remaining: int = 0
    reset: int = 0


class TpdRateLimitState(BaseModel):
    PERIOD_SECONDS: ClassVar[int] = 86_400

    value: int | None = None
    remaining: int = 0
    reset: int = 0


class RpmRateLimitState(BaseModel):
    PERIOD_SECONDS: ClassVar[int] = 60

    value: int | None = 0
    remaining: int = 0
    reset: int = 0


class RpdRateLimitState(BaseModel):
    PERIOD_SECONDS: ClassVar[int] = 86_400

    value: int | None = 0
    remaining: int = 0
    reset: int = 0


type RateLimitWindowState = TpmRateLimitState | TpdRateLimitState | RpmRateLimitState | RpdRateLimitState


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
    def unlimited(cls) -> "RouterRateLimitState":
        return cls(
            tpm=TpmRateLimitState(value=None),
            tpd=TpdRateLimitState(value=None),
            rpm=RpmRateLimitState(value=None),
            rpd=RpdRateLimitState(value=None),
        )

    def build_limit_headers(self, prompt_tokens: int, charged: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {}
        request_cost = 1 if charged else 0
        token_cost = prompt_tokens if charged else 0

        requests_window = self._most_restrictive_limit(self.rpm, self.rpd)
        if requests_window is not None:
            headers.update(self._window_headers(window=requests_window, family="requests", cost=request_cost))

        tokens_window = self._most_restrictive_limit(self.tpm, self.tpd)
        if tokens_window is not None:
            headers.update(self._window_headers(window=tokens_window, family="tokens", cost=token_cost))

        return headers

    @staticmethod
    def _most_restrictive_limit(*windows: RateLimitWindowState) -> RateLimitWindowState | None:
        configured = [window for window in windows if window.value is not None]
        if not configured:
            return None

        return min(configured, key=lambda window: window.remaining)

    @classmethod
    def _window_headers(cls, window: RateLimitWindowState, family: str, cost: int) -> dict[str, str]:
        return {
            f"x-ratelimit-limit-{family}": str(window.value),
            f"x-ratelimit-remaining-{family}": str(max(0, window.remaining - cost)),
            f"x-ratelimit-reset-{family}": cls._format_duration(
                cls._reset_in_seconds(reset_epoch=window.reset, period_seconds=window.PERIOD_SECONDS)
            ),
        }

    @staticmethod
    def _reset_in_seconds(reset_epoch: float, period_seconds: int) -> int:
        if reset_epoch <= 0:
            # reset 0 means the window has not started: it will last the full period
            return period_seconds

        return max(0, int(reset_epoch - datetime.now(UTC).timestamp()))

    @staticmethod
    def _format_duration(seconds: int) -> str:
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h{minutes}m{secs}s"

        if minutes:
            return f"{minutes}m{secs}s"

        return f"{secs}s"
