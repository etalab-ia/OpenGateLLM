from dataclasses import dataclass
import time

from api.domain.model.entities import Model, ModelCosts
from api.domain.model.errors import ModelNotFoundError
from api.domain.router import RouterRepository
from api.domain.router.entities import Router
from api.domain.router.errors import RouterNotFoundError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError


@dataclass
class GetModelUseCaseSucess:
    model: Model


@dataclass
class GetModelCommand:
    user_id: int
    name: str


type GetModelUseCaseResult = GetModelUseCaseSucess | ModelNotFoundError | UserExpiredError


class GetModelUseCase:
    def __init__(self, router_repository: RouterRepository, user_with_role_query: UserWithRoleQuery):
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: GetModelCommand) -> GetModelUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.user_id)
        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=command.name)
        match result:
            case Router() as router:
                pass
            case RouterNotFoundError():
                return ModelNotFoundError(name=command.name)

        if router.has_no_providers or user.cannot_access_router(router_id=router.id):
            return ModelNotFoundError(name=command.name)

        organization_name = await self.router_repository.get_organization_name(router.user_id)
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
