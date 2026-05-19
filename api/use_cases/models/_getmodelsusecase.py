from dataclasses import dataclass
import time

from api.domain.model.entities import Model, ModelCosts
from api.domain.model.errors import ModelNotFoundError
from api.domain.router import RouterRepository
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError


@dataclass
class GetModelUseCaseSucess:
    models: list[Model]


type Result = GetModelUseCaseSucess | ModelNotFoundError | UserExpiredError


class GetModelsUseCase:
    def __init__(self, user_id: int, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.user_id = user_id
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, name: str | None = None) -> Result:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=self.user_id)
        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        models = []

        routers = await self.router_repository.get_all_routers()

        if name is not None:
            routers = [router for router in routers if router.name == name or any(alias == name for alias in router.aliases)]
            if not routers:
                return ModelNotFoundError()

        for router in routers:
            if router.has_no_providers:
                continue
            if user.cannot_access_router(router_id=router.id):
                continue

            organization_name = await self.router_repository.get_organization_name(router.user_id)
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

        if name is not None and len(models) == 0:
            return ModelNotFoundError()  # TODO: create a dedicated use case
        return GetModelUseCaseSucess(models=models)
