from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.auth import SsoPolicyRepository
from api.domain.auth.entities import (
    NewSsoPolicy,
    NewSsoPolicyRule,
    SsoAccessRuleType,
    SsoPolicy,
    SsoPolicyEmailRule,
    SsoPolicyOrganizationRule,
    SsoPolicyRoleRule,
    SsoPolicyRule,
)
from api.domain.auth.errors import SsoPolicyRuleAlreadyExistsError, SsoPolicyRuleNotFoundError
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.sql.models import SsoPolicyRule as SsoPolicyRuleTable


class PostgresSsoPolicyRepository(SsoPolicyRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _rule_to_row(rule: NewSsoPolicyRule) -> dict:
        row = {"type": rule.type, "value": rule.value, "role_id": None, "organization_id": None}
        if hasattr(rule, "role_id"):
            row["role_id"] = rule.role_id
        if hasattr(rule, "organization_id"):
            row["organization_id"] = rule.organization_id

        return row

    @staticmethod
    def _row_to_rule(row: SsoPolicyRuleTable) -> SsoPolicyRule:
        kwargs = {"id": row.id, "type": row.type, "value": row.value, "created": row.created, "updated": row.updated}
        match row.type:
            case SsoAccessRuleType.EMAIL:
                return SsoPolicyEmailRule(**kwargs)
            case SsoAccessRuleType.ORGANIZATION:
                return SsoPolicyOrganizationRule(**kwargs, organization_id=row.organization_id)
            case SsoAccessRuleType.ROLE:
                return SsoPolicyRoleRule(**kwargs, role_id=row.role_id)

    async def get_policy(self) -> SsoPolicy:
        rules_result = await self.postgres_session.execute(select(SsoPolicyRuleTable))
        rules = [self._row_to_rule(row) for row in rules_result.scalars().all()]

        return SsoPolicy(rules=rules)

    async def replace_policy(
        self, policy: NewSsoPolicy
    ) -> SsoPolicy | SsoPolicyRuleAlreadyExistsError | RoleNotFoundError | OrganizationNotFoundError:
        await self.postgres_session.execute(delete(SsoPolicyRuleTable))
        rows = [self._rule_to_row(rule) for rule in policy.rules]
        if rows:
            try:
                await self.postgres_session.execute(insert(SsoPolicyRuleTable), rows)
            except IntegrityError as e:
                if "unique_sso_policy_type_value" in str(e.orig):
                    return SsoPolicyRuleAlreadyExistsError()
                if "sso_policy_rule_role_id_fkey" in str(e.orig):
                    return RoleNotFoundError()
                if "sso_policy_rule_organization_id_fkey" in str(e.orig):
                    return OrganizationNotFoundError()
                raise

        return await self.get_policy()

    async def update_policy_rule(
        self,
        rule: NewSsoPolicyRule,
    ) -> SsoPolicyRule | RoleNotFoundError | OrganizationNotFoundError | SsoPolicyRuleAlreadyExistsError | SsoPolicyRuleNotFoundError:
        row_dict = self._rule_to_row(rule)
        try:
            result = await self.postgres_session.execute(
                update(SsoPolicyRuleTable).where(SsoPolicyRuleTable.id == rule.id).values(**row_dict).returning(SsoPolicyRuleTable)
            )
            row = result.scalar_one_or_none()
        except IntegrityError as e:
            if "unique_sso_policy_type_value" in str(e.orig):
                return SsoPolicyRuleAlreadyExistsError()
            if "sso_policy_rule_role_id_fkey" in str(e.orig):
                return RoleNotFoundError(id=rule.role_id)
            if "sso_policy_rule_organization_id_fkey" in str(e.orig):
                return OrganizationNotFoundError(id=rule.organization_id)
            raise

        if row is None:
            return SsoPolicyRuleNotFoundError()

        return self._row_to_rule(row)
