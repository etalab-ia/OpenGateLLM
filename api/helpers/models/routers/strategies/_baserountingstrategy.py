from abc import ABC, abstractmethod
from typing import List

from api.clients.model import BaseModelClient as ModelClient


class BaseRoutingStrategy(ABC):
    def __init__(self, clients: List[ModelClient]) -> None:
        self.clients = clients

    @abstractmethod
    def choose_model_client(self) -> tuple[ModelClient, float | None]:
        """
        Choose a client among the model's clients list

        Returns:
           BaseModelClient: The chosen client
        """
        pass
