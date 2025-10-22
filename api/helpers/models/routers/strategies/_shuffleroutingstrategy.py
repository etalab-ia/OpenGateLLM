import random

from api.clients.model import BaseModelClient as ModelClient
from api.helpers.models.routers.strategies import BaseRoutingStrategy


class ShuffleRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: list[ModelClient]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> tuple[ModelClient, float | None]:
        return random.choice(self.clients), None
