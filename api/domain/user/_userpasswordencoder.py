from abc import ABC, abstractmethod


class UserPasswordEncoder(ABC):
    @abstractmethod
    def encode_password(self, password: str) -> str:
        pass

    @abstractmethod
    def validate_password(self, password: str, encoded_password: str) -> bool:
        pass
