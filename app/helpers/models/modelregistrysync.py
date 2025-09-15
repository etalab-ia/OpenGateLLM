from typing import Callable, Union, Awaitable
from typing import Callable, Union, Awaitable, TYPE_CHECKING

from app.helpers.models._basemodelregistry import ModelRegistryBase

from app.utils.exceptions import ModelNotFoundException

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class ModelRegistrySync(ModelRegistryBase):
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

            return await model_router.safe_client_access(
                endpoint=endpoint,
                handler=handler
            )
