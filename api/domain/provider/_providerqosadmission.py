from abc import ABC, abstractmethod
from dataclasses import dataclass

from api.domain.provider.entities import Provider
from api.domain.router.entities import RouterLoadBalancingStrategy


@dataclass(frozen=True)
class QosAdmissionGranted:
    provider_id: int


@dataclass(frozen=True)
class QosAdmissionFull:
    depth: int


type QosAdmissionResult = QosAdmissionGranted | QosAdmissionFull


class ProviderQosAdmission(ABC):
    @abstractmethod
    async def try_admit(
        self,
        providers: list[Provider],
        strategy: RouterLoadBalancingStrategy,
        request_id: str,
    ) -> QosAdmissionResult:
        pass

    @abstractmethod
    async def start_heartbeat(self, provider_id: int, request_id: str) -> None:
        pass

    @abstractmethod
    async def release(self, provider_id: int, request_id: str) -> None:
        pass
