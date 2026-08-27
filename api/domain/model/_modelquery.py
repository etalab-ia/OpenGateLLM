from abc import ABC, abstractmethod

from api.domain.model.errors import ModelNotFoundError
from api.domain.model.views import ModelView


class ModelQuery(ABC):
    @abstractmethod
    async def get_models(self) -> list[ModelView]:
        pass

    @abstractmethod
    async def get_model_by_name_or_alias(self, name: str) -> ModelView | ModelNotFoundError:
        pass
