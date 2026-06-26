from dataclasses import dataclass

from api.domain.auth import SsoPolicyRepository
from api.domain.auth.entities import NewSsoPolicy, SsoPolicy
from api.domain.auth.errors import SsoPolicyRuleAlreadyExistsError
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError


@dataclass
class UpdateSsoPolicyCommand:
    policy: NewSsoPolicy


@dataclass
class UpdateSsoPolicyUseCaseSuccess:
    policy: SsoPolicy


type UpdateSsoPolicyUseCaseResult = UpdateSsoPolicyUseCaseSuccess | OrganizationNotFoundError | RoleNotFoundError | SsoPolicyRuleAlreadyExistsError


class UpdateSsoPolicyUseCase:
    def __init__(self, sso_policy_repository: SsoPolicyRepository):
        self.sso_policy_repository = sso_policy_repository

    async def execute(self, command: UpdateSsoPolicyCommand) -> UpdateSsoPolicyUseCaseResult:

        result = await self.sso_policy_repository.replace_policy(policy=command.policy)
        match result:
            case SsoPolicy() as policy:
                return UpdateSsoPolicyUseCaseSuccess(policy=policy)
            case error:
                return error
