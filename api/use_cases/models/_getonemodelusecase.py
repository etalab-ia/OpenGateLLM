from dataclasses import dataclass

from api.domain.model import ModelQuery
from api.domain.model.errors import ModelNotFoundError
from api.domain.model.views import ModelView
from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetOneModelUseCaseSuccess:
    model: ModelView


@dataclass
class GetOneModelCommand:
    authenticated_user: AuthenticatedUserView
    name: str


type GetOneModelUseCaseResult = GetOneModelUseCaseSuccess | ModelNotFoundError


class GetOneModelUseCase:
    def __init__(self, model_query: ModelQuery):
        self.model_query = model_query

    async def execute(self, command: GetOneModelCommand) -> GetOneModelUseCaseResult:
        result = await self.model_query.get_model_by_name_or_alias(name=command.name)
        match result:
            case ModelView() as model:
                pass
            case ModelNotFoundError() as error:
                return error

        if command.authenticated_user.cannot_access_router(router_id=model.router_id):
            return ModelNotFoundError(name=command.name)

        return GetOneModelUseCaseSuccess(model=model)
