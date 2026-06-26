from dataclasses import dataclass

from api.domain.auth import SsoPolicyRepository
from api.domain.auth.entities import SsoPolicy


@dataclass
class GetSsoPolicyUseCaseSuccess:
    policy: SsoPolicy


class GetSsoPolicyUseCase:
    def __init__(self, sso_policy_repository: SsoPolicyRepository):
        self.sso_policy_repository = sso_policy_repository

    async def execute(self) -> GetSsoPolicyUseCaseSuccess:
        policy = await self.sso_policy_repository.get_policy()
        return GetSsoPolicyUseCaseSuccess(policy=policy)
