from abc import ABC, abstractmethod


class AuthSsoProviderCache(ABC):
    @abstractmethod
    async def get(self, email: str) -> dict | None:
        pass

    @abstractmethod
    async def set(self, email: str, claims: dict, expire: int) -> None:
        pass

    @abstractmethod
    async def delete(self, email: str) -> None:
        pass
