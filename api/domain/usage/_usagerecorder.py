from abc import ABC, abstractmethod


class UsageRecorder(ABC):
    @abstractmethod
    def record_router(self, router_id: int, router_name: str) -> None:
        pass

    @abstractmethod
    def record_provider(self, provider_id: int, provider_model_name: str) -> None:
        pass

    @abstractmethod
    def record_usage(self, request_id: str | None, prompt_tokens: int, completion_tokens: int, cost: float) -> None:
        pass
