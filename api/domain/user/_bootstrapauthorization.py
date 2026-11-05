from abc import ABC, abstractmethod


class BootstrapAuthorization(ABC):
    @abstractmethod
    async def attach_bootstrap_admin_to_platform(self, user_id: int) -> None:
        pass
