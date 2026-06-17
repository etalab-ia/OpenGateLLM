from dataclasses import dataclass

from api.domain.model.entities import Model, ModelCosts
from api.domain.router import RouterRepository
from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetModelsUseCaseSucess:
    models: list[Model]


@dataclass
class GetModelsCommand:
    authenticated_user: AuthenticatedUserView


type GetModelsUseCaseResult = GetModelsUseCaseSucess


class GetModelsUseCase:
    def __init__(self, router_repository: RouterRepository):
        self.router_repository = router_repository

    async def execute(self, command: GetModelsCommand) -> GetModelsUseCaseResult:
        models = []
        routers = await self.router_repository.get_all_routers()

        for router in routers:
            if router.has_no_providers:
                continue
            if command.authenticated_user.cannot_access_router(router_id=router.id):
                continue

            organization_name = await self.router_repository.get_organization_name(router.user_id)  # @TODO: replace by organization repository
            models.append(
                Model(
                    id=router.name,
                    type=router.type,
                    owned_by=organization_name,
                    aliases=router.aliases,
                    created=router.created,
                    max_context_length=router.max_context_length,
                    costs=ModelCosts(prompt_tokens=router.cost_prompt_tokens, completion_tokens=router.cost_completion_tokens),
                )
            )

        return GetModelsUseCaseSucess(models=models)
