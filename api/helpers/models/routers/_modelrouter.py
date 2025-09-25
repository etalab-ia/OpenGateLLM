from asyncio import Lock
from fastapi import HTTPException
import time
from typing import Callable, Union, Awaitable
import inspect
import logging

from api.clients.model import BaseModelClient as ModelClient
from api.helpers.models.routers.strategies import LeastBusyRoutingStrategy, RoundRobinRoutingStrategy, ShuffleRoutingStrategy
from api.schemas.models import ModelType
from api.utils.exceptions import WrongModelTypeException
from api.utils.tracked_cycle import TrackedCycle
from api.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK

from api.schemas.core.configuration import Model as ModelRouterSchema, RoutingStrategy

logger = logging.getLogger(__name__)


class ModelRouter:
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        ENDPOINT__OCR: [ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

    def __init__(
        self,
        name: str,
        type: ModelType,
        owned_by: str,
        aliases: list[str],
        routing_strategy: str,
        providers: list[ModelClient],
        cycle_offset: int = 0,
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
        prompt_tokens = max(costs_prompt_tokens) if costs_prompt_tokens else 0.0
        completion_tokens = max(costs_completion_tokens) if costs_completion_tokens else 0.0

        # set attributes of the model (returned by /v1/models endpoint)
        self.name = name
        self.type = type
        self.owned_by = owned_by
        self.created = round(time.time())
        self.aliases = aliases
        self.max_context_length = max_context_length
        self.cost_prompt_tokens = prompt_tokens
        self.cost_completion_tokens = completion_tokens

        self._vector_size = vector_sizes[0] if vector_sizes else None
        self._routing_strategy = routing_strategy
        self._providers = providers
        self._cycle = TrackedCycle(providers, cycle_offset)

        self._lock = Lock()

    async def as_schema(self, censored: bool = True) -> ModelRouterSchema:
        """
        Gets a ModelRouterSchema that represents the current instance.

        Args:
            censored(bool): Whether sensitive information needs to be hidden.
        """

        providers = await self.get_clients()
        schemas = []

        for p in providers:
            schemas.append(p.as_schema(censored))

        return ModelRouterSchema(
            name=self.name,
            type=self.type,
            owned_by=self.owned_by,
            aliases=self.aliases,
            routing_strategy=RoutingStrategy(self._routing_strategy),
            vector_size=self._vector_size,
            max_context_length=self.max_context_length,
            created=self.created,
            cycle_offset=self._cycle.offset,
            providers=schemas,
        )

    @staticmethod
    def from_schema(schema: ModelRouterSchema, **init_kwargs) -> "ModelRouter":
        providers = [ModelClient.from_schema(schema=p) for p in schema.providers]

        return ModelRouter(
            name=schema.name,
            type=schema.type,
            owned_by=schema.owned_by,
            aliases=schema.aliases,
            routing_strategy=schema.routing_strategy,
            providers=providers,
            cycle_offset=schema.cycle_offset,
            **init_kwargs,
        )

    def get_client(self, endpoint: str) -> tuple[ModelClient, float | None]:
        """
        Get a client to handle the request.
        NB: this method is not thread-safe, you probably want to use safe_client_access.

        Args:
            endpoint(str): The type of endpoint called

        Returns:
            ModelClient: The available client
            float | None: the performance indicator of the chosen server, if applicable
        """
        if endpoint and self.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if self._routing_strategy == RoutingStrategy.ROUND_ROBIN:
            strategy = RoundRobinRoutingStrategy(self._providers, self._cycle)
        elif self._routing_strategy == RoutingStrategy.LEAST_BUSY:
            strategy = LeastBusyRoutingStrategy(self._providers, "time_to_first_token")
        else:
            strategy = ShuffleRoutingStrategy(self._providers)

        client, metric = strategy.choose_model_client()
        client.endpoint = endpoint

        return client, metric

    async def get_clients(self):
        """
        Return the current list of ModelClient thread-safely.
        """
        async with self._lock:
            return self._providers

    async def add_client(self, client: ModelClient):
        """
        Adds a new client.
        """
        async with self._lock:
            for c in self._providers:
                if c.url == client.url and c.name == client.name:  # The client already exists; we don't want to double it
                    return

            # consistency check
            assert client.vector_size == self._vector_size, "All embeddings models in the same model group must have the same vector size."

            self._providers.append(client)

            if client.max_context_length is not None:
                if self.max_context_length is None:
                    self.max_context_length = client.max_context_length
                else:
                    self.max_context_length = min(self.max_context_length, client.max_context_length)

            self._cycle = TrackedCycle(self._providers)
            self.cost_prompt_tokens = max(self.cost_prompt_tokens, client.cost_prompt_tokens)
            self.cost_completion_tokens = max(self.cost_completion_tokens, client.cost_completion_tokens)

    async def delete_client(self, api_url: str, name: str) -> bool:
        """
        Delete a client.

        Returns:
            True if the router still has active ModelClients
            False otherwise
        """
        async with self._lock:
            client = None
            cost_prompt_tokens = float("-inf")
            cost_completion_tokens = float("-inf")
            max_context_length = float("+inf")

            for c in self._providers:
                if c.url == api_url and c.name == name:
                    client = c
                else:
                    if c.max_context_length is not None and c.max_context_length < max_context_length:
                        max_context_length = c.max_context_length

                    if c.cost_prompt_tokens > cost_prompt_tokens:
                        cost_prompt_tokens = c.cost_prompt_tokens

                    if c.cost_completion_tokens > cost_completion_tokens:
                        cost_completion_tokens = c.cost_completion_tokens

            if client is None:
                raise HTTPException(status_code=404, detail=f'Model with name "{name}" and URL "{api_url}" not found')

            await client.lock.acquire()
            try:
                self._providers.remove(client)

                if len(self._providers) == 0:
                    # No more clients, the ModelRouter is about to get deleted.
                    # There is no need to try to "update" it further.
                    # NB: there is no chance that another ModelClient gets added right after,
                    # as ModelRegistry's requires its lock for the whole removing process.
                    # If needed, "this" router will be recreated.
                    return False

                self._cycle = TrackedCycle(self._providers)
                self.cost_prompt_tokens = cost_prompt_tokens
                self.cost_completion_tokens = cost_completion_tokens
                self.max_context_length = max_context_length
            finally:
                # Ensure the client lock is released even if an error occurs above.
                try:
                    if client.lock.locked():
                        client.lock.release()
                except Exception:
                    logger.exception("Unexpected error while releasing client lock")
            return True

    async def add_alias(self, alias: str):
        """
        Thread-safely adds an alias.
        """
        async with self._lock:
            if alias not in self.aliases:  # Silent error?
                self.aliases.append(alias)

    async def delete_alias(self, alias):
        """
        Thread-safely removes an alias.
        """
        async with self._lock:
            if alias in self.aliases:  # Silent error?
                self.aliases.remove(alias)

    async def safe_client_access[R](self, endpoint: str, handler: Callable[[ModelClient], Union[R, Awaitable[R]]]) -> R:
        """
        Thread-safely access a BaseModelClient.
        This method calls the given callback with the current instance and BaseModelClient
            lock acquired just in time, to prevent race conditions on the selected BaseModelClient.
        Unattended disconnections may still happen (the function may raise an HTTPException).
        """
        async with self._lock:
            client, _ = self.get_client(endpoint)
            # Client lock is acquired within this block to prevent
            # another thread to remove it while in use
            await client.lock.acquire()

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(client)
            else:
                result = handler(client)
        finally:
            # Always release the client lock, even if handler raises
            client.lock.release()

        return result
