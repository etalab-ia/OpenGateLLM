from api.domain.role.entities import PermissionType
from api.domain.router import RouterRepository
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.domain.userinfo import UserInfoRepository
from api.tasks import add_model_queue_to_running_worker
from api.utils.exceptions import InsufficientPermissionException, RouterAliasAlreadyExistsException
from api.utils.variables import PREFIX__CELERY_QUEUE_ROUTING


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository
        self.queuing_enabled = False

    async def execute(
        self,
        user_id: int,
        name: str,
        router_type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
    ) -> Router:
        user_info = await self.user_info_repository.get_user_info(user_id=user_id)

        await self._check_permissions(permissions=user_info.permissions)

        existing_aliases = await self.router_repository.get_aliases(aliases)
        if len(existing_aliases) != 0:
            raise RouterAliasAlreadyExistsException()

        router = await self.router_repository.create_router(
            name=name,
            router_type=router_type,
            aliases=aliases,
            load_balancing_strategy=load_balancing_strategy,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
            user_id=user_info.id,
        )

        if aliases:
            await self.router_repository.insert_aliases(aliases, router.id)

        if self.queuing_enabled:
            add_model_queue_to_running_worker(queue_name=f"{PREFIX__CELERY_QUEUE_ROUTING}.{router.id}")

        return router

    async def _check_permissions(self, permissions: list[PermissionType]) -> None:
        if [PermissionType.ADMIN] and not set(permissions).intersection({PermissionType.ADMIN}):
            raise InsufficientPermissionException()
