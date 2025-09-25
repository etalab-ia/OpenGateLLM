from api.clients.model import BaseModelClient as ModelClient
from api.helpers.models.routers.strategies import BaseRoutingStrategy
from api.utils.tracked_cycle import TrackedCycle


class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: list[ModelClient], cycle: TrackedCycle) -> None:
        super().__init__(clients)
        self.cycle = cycle

    def choose_model_client(self) -> tuple[ModelClient, float | None]:
        return next(self.cycle), None
