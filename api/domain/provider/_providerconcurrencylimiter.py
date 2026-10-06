from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


@dataclass(frozen=True)
class ProviderReservation:
    provider: Provider
    request_id: str


@dataclass(frozen=True)
class ProviderReservationRefused:
    pass


type ProviderReservationResult = ProviderReservation | ProviderReservationRefused


class ProviderConcurrencyLimiter(ABC):
    @abstractmethod
    async def reserve(
        self,
        request_id: str,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        enforce_limit: bool,
    ) -> ProviderReservationResult:
        """Choose one of the providers and hold a place on it until release() is called.

        request_id identifies the reservation and must be unique per request. A provider whose limit is 0 is closed and
        never chosen, even when enforce_limit is False.
        """

    @abstractmethod
    async def release(self, reservation: ProviderReservation) -> None:
        pass

    @abstractmethod
    async def get_loads(self, provider_ids: list[int]) -> dict[int, int]:
        pass
