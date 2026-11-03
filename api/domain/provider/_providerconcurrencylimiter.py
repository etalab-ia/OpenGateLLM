from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.provider.entities import Provider, ProviderLoads


@dataclass(frozen=True)
class ProviderReservation:
    provider: Provider
    request_id: str


@dataclass(frozen=True)
class ProviderReservationRefused:
    pass


@dataclass(frozen=True)
class ProviderLimitsCannotBeEnforced:
    pass


type ProviderReservationResult = ProviderReservation | ProviderReservationRefused


class ProviderConcurrencyLimiter(ABC):
    @abstractmethod
    async def read_loads(self, providers: list[Provider]) -> ProviderLoads | ProviderLimitsCannotBeEnforced:
        pass

    @abstractmethod
    async def reserve(
        self, request_id: str, provider: Provider, limit: int | None
    ) -> ProviderReservation | ProviderReservationRefused | ProviderLimitsCannotBeEnforced:
        """Hold a place on the provider until release() is called, unless it already holds `limit` requests.

        request_id identifies the reservation and must be unique per request. A `limit` of None is not enforced.
        """

    @abstractmethod
    async def release(self, reservation: ProviderReservation) -> None:
        pass
