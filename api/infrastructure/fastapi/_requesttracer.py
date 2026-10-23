from abc import ABC, abstractmethod

from api.domain.usage.entities import UsageRecord


class RequestTracer(ABC):
    """An implementation logs its own failures and never raises: a trace that fails must not fail the request it observes."""

    @abstractmethod
    def start(self, record: UsageRecord) -> None:
        pass

    @abstractmethod
    def end(self, record: UsageRecord) -> None:
        pass


class NoOpRequestTracer(RequestTracer):
    def start(self, record: UsageRecord) -> None:
        pass

    def end(self, record: UsageRecord) -> None:
        pass
