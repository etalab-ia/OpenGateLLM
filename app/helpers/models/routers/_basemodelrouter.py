from abc import ABC, abstractmethod
from itertools import cycle
import time

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.models import ModelType


class BaseModelRouter(ABC):
    def __init__(
        self,
        name: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        providers: list[ModelClient],
        *args,
        **kwargs,
    ) -> None:
        vector_sizes, max_context_lengths, costs_prompt_tokens, costs_completion_tokens = list(), list(), list(), list()

        for provider in providers:
            vector_sizes.append(provider.vector_size)
            max_context_lengths.append(provider.max_context_length)
            costs_prompt_tokens.append(provider.cost_prompt_tokens)
            costs_completion_tokens.append(provider.cost_completion_tokens)

        # consistency checks
        assert len(set(vector_sizes)) < 2, "All embeddings models in the same model group must have the same vector size."

        # if there are several models with different max_context_length, it will return the minimal value for consistency of /v1/models response
        max_context_lengths = [value for value in max_context_lengths if value is not None]
        max_context_length = min(max_context_lengths) if max_context_lengths else None

        # if there are several models with different costs, it will return the max value for consistency of /v1/models response
        prompt_tokens = max(costs_prompt_tokens)
        completion_tokens = max(costs_completion_tokens)

        # set attributes of the model (returned by /v1/models endpoint)
        self.name = name
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length
        self.cost_prompt_tokens = prompt_tokens
        self.cost_completion_tokens = completion_tokens

        self._vector_size = vector_sizes[0]
        self._routing_strategy = routing_strategy
        self._cycle = cycle(providers)
        self._providers = providers

    @abstractmethod
    def get_client(self, endpoint: str) -> ModelClient:
        """
        Get a client to handle the request

        Args:
            endpoint(str): The type of endpoint called

        Returns:
            BaseModelClient: The available client
        """
        pass
