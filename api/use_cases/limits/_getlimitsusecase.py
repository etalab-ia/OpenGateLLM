from dataclasses import dataclass

from api.domain.model import ModelQuery
from api.domain.role.entities import LimitType
from api.domain.router import RouterRateLimiter
from api.domain.router.entities import RouterRateLimitState
from api.domain.router.views import RouterLimitsView, RouterLimitView
from api.domain.user.views import AuthenticatedUserView


@dataclass
class GetLimitsCommand:
    authenticated_user: AuthenticatedUserView


@dataclass
class GetLimitsUseCaseSuccess:
    limits: list[RouterLimitsView]


type GetLimitsUseCaseResult = GetLimitsUseCaseSuccess


class GetLimitsUseCase:
    def __init__(self, model_query: ModelQuery, router_rate_limiter: RouterRateLimiter):
        self.model_query = model_query
        self.router_rate_limiter = router_rate_limiter

    async def execute(self, command: GetLimitsCommand) -> GetLimitsUseCaseResult:
        user = command.authenticated_user
        models = await self.model_query.get_models()

        limits = []
        for model in models:
            if user.cannot_access_router(router_id=model.router_id):
                continue

            if user.is_admin:
                state = RouterRateLimitState.unlimited()
            else:
                state = await self.router_rate_limiter.get_rate_limit_state(
                    user_id=user.id, router_limits=user.limits_for(router_id=model.router_id), router_id=model.router_id
                )

            router_limits = []
            for limit_type in LimitType:
                window = getattr(state, limit_type.value)
                router_limits.append(RouterLimitView(type=limit_type, value=window.value, remaining=window.remaining))

            limits.append(RouterLimitsView(router_id=model.router_id, model=model.id, limits=router_limits))

        return GetLimitsUseCaseSuccess(limits=limits)
