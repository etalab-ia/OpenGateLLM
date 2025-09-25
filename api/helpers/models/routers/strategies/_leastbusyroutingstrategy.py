from typing import Literal
from datetime import datetime, timedelta
import math
import random

from api.helpers.models.routers.strategies import BaseRoutingStrategy

from api.clients.model import BaseModelClient as ModelClient


class LeastBusyRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: list[ModelClient], metric_type: Literal["time_to_first_token", "latency"]) -> None:
        super().__init__(clients)
        self.metric_type: Literal["time_to_first_token", "latency"] = metric_type

    @staticmethod
    def get_percentile(series: list[tuple[int, float]], percentile: float = 0.95) -> float:
        """
        Return a value such that at least 95% of series values are smaller.
        series: list of (datetime, value) tuples
        """
        if not series:
            raise ValueError("Series is empty")

        values = [v for _, v in series]
        values.sort()

        idx = math.ceil(percentile * len(values)) - 1
        return values[idx]

    def get_server_score(self, client: ModelClient) -> float:
        cutoff = datetime.now() - timedelta(hours=1)
        series = client.get_timeseries_since(self.metric_type, cutoff)
        return LeastBusyRoutingStrategy.get_percentile(series)

    @staticmethod
    def least_busy(scores: dict[ModelClient, float]) -> tuple[ModelClient, float]:
        """
        scores is a dict of shape {url: score} for each server
        """
        min_value = min(scores.values())
        candidates = [k for k, v in scores.items() if v == min_value]
        return random.choice(candidates), min_value

    def choose_model_client(self) -> tuple[ModelClient, float | None]:
        scores = {}
        for client in self.clients:
            scores[client] = self.get_server_score(client)
        return LeastBusyRoutingStrategy.least_busy(scores)
