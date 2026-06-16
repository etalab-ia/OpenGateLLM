from dataclasses import dataclass

from api.domain.model.entities import Model, ModelCosts
from api.domain.model.errors import ModelNotFoundError
from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetModelUseCaseSucess:
    model: Model


@dataclass
class GetModelCommand:
    authenticated_user: AuthenticatedUserView
    name: str


type GetModelUseCaseResult = GetModelUseCaseSucess | ModelNotFoundError


class GetModelUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: GetModelCommand) -> GetModelUseCaseResult:
        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=command.name)
        match result:
            case Router() as router:
                pass
            case RouterNotFoundError():
                return ModelNotFoundError(name=command.name)

        if router.has_no_providers or command.authenticated_user.cannot_access_router(router_id=router.id):
            return ModelNotFoundError(name=command.name)

        organization_name = await self.router_repository.get_organization_name(router.user_id)  # @TODO: replace by organization repository
        model = Model(
            id=router.name,
            type=router.type,
            owned_by=organization_name,
            aliases=router.aliases,
            created=router.created,
            max_context_length=router.max_context_length,
            costs=ModelCosts(prompt_tokens=router.cost_prompt_tokens, completion_tokens=router.cost_completion_tokens),
        )

        return GetModelUseCaseSucess(model=model)
