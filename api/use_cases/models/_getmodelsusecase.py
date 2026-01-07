from dataclasses import dataclass

from api.domain.router import RouterRepository
from api.domain.router.entities import Model, ModelCosts
from api.domain.userinfo import UserInfoRepository


@dataclass
class Success:
    models: list[Model]


@dataclass
class ModelNotFound:
    pass


type Result = Success | ModelNotFound


class GetModelsUseCase:
    def __init__(self, user_id: int, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.user_id = user_id
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(self, name: str | None = None) -> Result:
        user_info = await self.user_info_repository.get_user_info(user_id=self.user_id)
        models = []

        routers = await self.router_repository.get_all_routers()

        if name is not None:
            routers = [router for router in routers if router.name == name or any(alias == name for alias in router.aliases)]
            if not routers:
                return ModelNotFound()

        for router in routers:
            if router.providers > 0:
                router_limit = next((limit for limit in user_info.limits if limit.router == router.id), None)
                has_access = router_limit is not None and (router_limit.value is None or router_limit.value > 0)
                if has_access:
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
            return ModelNotFound()
        return Success(models=models)
