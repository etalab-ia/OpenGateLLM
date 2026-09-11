from abc import ABC, abstractmethod


class ClientConnection(ABC):
    @abstractmethod
    async def is_disconnected(self) -> bool:
        pass
