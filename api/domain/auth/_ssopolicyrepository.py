from abc import ABC, abstractmethod

from api.domain.auth.entities import NewSsoPolicy, SsoPolicy
from api.domain.auth.errors import SsoPolicyRuleAlreadyExistsError
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError


class SsoPolicyRepository(ABC):
    @abstractmethod
    async def get_policy(self) -> SsoPolicy:
        pass

    @abstractmethod
    async def replace_policy(
        self, policy: NewSsoPolicy
    ) -> SsoPolicy | RoleNotFoundError | OrganizationNotFoundError | SsoPolicyRuleAlreadyExistsError:
        pass
