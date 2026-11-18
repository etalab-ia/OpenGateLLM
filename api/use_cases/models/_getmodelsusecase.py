from dataclasses import dataclass

from api.domain.model import ModelQuery
from api.domain.model.views import ModelView
from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetModelsUseCaseSucess:
    models: list[ModelView]


@dataclass
class GetModelsCommand:
    authenticated_user: AuthenticatedUserView


type GetModelsUseCaseResult = GetModelsUseCaseSucess


class GetModelsUseCase:
    def __init__(self, model_query: ModelQuery):
        self.model_query = model_query

    async def execute(self, command: GetModelsCommand) -> GetModelsUseCaseResult:
        models = await self.model_query.get_models()

        return GetModelsUseCaseSucess(models=[model for model in models if command.authenticated_user.can_access_router(router_id=model.router_id)])
