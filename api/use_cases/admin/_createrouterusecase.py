from dataclasses import dataclass

from api.domain.role.entities import PermissionType
from api.domain.router import RouterRepository
from api.domain.router._routerrepository import RouterNameAlreadyExists
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.domain.userinfo import UserInfoRepository


@dataclass
class CreateRouterUseCaseSuccess:
    router: Router


@dataclass
class RouterAliasAlreadyExistsError:
    pass


@dataclass
class RouterNameAlreadyExistsError:
    name: str


@dataclass
class InsufficientPermissionError:
    pass


type CreateRouterUseCaseResult = (
    CreateRouterUseCaseSuccess | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError | InsufficientPermissionError
)


class CreateRouterUseCase:
    def __init__(self, router_repository: RouterRepository, user_info_repository: UserInfoRepository):
        self.router_repository = router_repository
        self.user_info_repository = user_info_repository

    async def execute(
        self,
        user_id: int,
        name: str,
        router_type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
    ) -> CreateRouterUseCaseResult:
        user_info = await self.user_info_repository.get_user_info(user_id=user_id)

        is_admin = self.is_admin(permissions=user_info.permissions)
        if not is_admin:
            return InsufficientPermissionError()
        existing_aliases = []
        if aliases:
            existing_aliases = await self.router_repository.get_aliases(aliases)
        if existing_aliases:
            return RouterAliasAlreadyExistsError()

        result = await self.router_repository.create_router(
            name=name,
            router_type=router_type,
            load_balancing_strategy=load_balancing_strategy,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
            user_id=user_info.id,
        )

        match result:
            case RouterNameAlreadyExists(name=name):
                return RouterNameAlreadyExistsError(name)
            case Router() as router:
                if aliases:
                    await self.router_repository.insert_aliases(aliases, router.id)
                    router.aliases = aliases

                return CreateRouterUseCaseSuccess(router)

    def is_admin(self, permissions: list[PermissionType]) -> bool:
        return PermissionType.ADMIN in permissions
