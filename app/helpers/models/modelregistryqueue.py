from asyncio import wait_for
from typing import Callable, Union, Awaitable, TYPE_CHECKING

import aio_pika

from app.helpers.models._workingcontext import WorkingContext

from app.utils.configuration import configuration
from app.utils.exceptions import ModelNotFoundException

from app.utils.rabbitmq import AsyncRabbitMQConnection

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient

from app.helpers.models._basemodelregistry import ModelRegistryBase

class ModelRegistryQueue(ModelRegistryBase):
    async def execute_request[R](
        self,
        router_id: str,
        endpoint: str,
        handler: Callable[["BaseModelClient"], Union[R, Awaitable[R]]]
    ) -> R:
        async with self._lock:
            router_id = self.aliases.get(router_id, router_id)

            if router_id not in self._router_ids:
                raise ModelNotFoundException()

            model_router = self._routers[router_id]

            ctx = WorkingContext(
                endpoint=endpoint,
                handler=handler
            )

            await model_router.register_context(ctx)

            try:
                await AsyncRabbitMQConnection().publish_default_exchange(
                    message=aio_pika.Message(body=ctx.id.encode('utf8')),
                    routing_key=model_router.queue_name
                )

                result = await wait_for(
                    ctx.result,
                    timeout=configuration.dependencies.rabbitmq.timeout
                )
                await model_router.pop_context(ctx)  # free space once finished
                return result

            except Exception as e:
                # prevent memory leaks
                await model_router.pop_context(ctx.id)
                raise e

