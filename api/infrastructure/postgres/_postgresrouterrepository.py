from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.router import RouterRepository
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable


class PostgresRouterRepository(RouterRepository):
    def __init__(self, postgres_session: AsyncSession, app_title: str):
        self.postgres_session = postgres_session
        self.app_title = app_title

    async def get_organization_name(self, user_id) -> str:
        query = (
            select(OrganizationTable.name.label("owned_by"))
            .join(UserTable, UserTable.organization_id == OrganizationTable.id)
            .where(UserTable.id == user_id)
        )
        result = await self.postgres_session.execute(query)
        owned_by = result.scalar_one_or_none()
        return owned_by if owned_by else self.app_title

    async def get_all_routers(self) -> list[Router]:
        routers = []
        provider_count_subquery = (
            select(func.count(ProviderTable.id)).where(ProviderTable.router_id == RouterTable.id).correlate(RouterTable).scalar_subquery()
        )
        # TODO: un router a plusieurs providers. Comment sont choisis max_content_length and vector_size ?
        query = (
            select(
                RouterTable.id,
                RouterTable.name,
                RouterTable.user_id,
                RouterTable.type,
                RouterTable.load_balancing_strategy,
                RouterTable.cost_prompt_tokens,
                RouterTable.cost_completion_tokens,
                ProviderTable.max_context_length,
                ProviderTable.vector_size,
                provider_count_subquery.label("providers"),
                cast(func.extract("epoch", RouterTable.created), Integer).label("created"),
                cast(func.extract("epoch", RouterTable.updated), Integer).label("updated"),
            )
            .distinct(RouterTable.id)
            .join(ProviderTable, ProviderTable.router_id == RouterTable.id, isouter=True)
            .order_by(RouterTable.id, ProviderTable.id)
        )

        result = await self.postgres_session.execute(query)
        router_results = [row._asdict() for row in result.all()]

        aliases = await self.get_all_aliases()

        for row in router_results:
            user_id = 0 if row["user_id"] is None else row["user_id"]  # 0 corresponds to master user ID
            routers.append(
                Router(
                    id=row["id"],
                    name=row["name"],
                    user_id=user_id,
                    type=ModelType(row["type"]),
                    aliases=aliases.get(row["id"], []),
                    load_balancing_strategy=RouterLoadBalancingStrategy(row["load_balancing_strategy"]),
                    vector_size=row["vector_size"],
                    max_context_length=row["max_context_length"],
                    cost_prompt_tokens=row["cost_prompt_tokens"] or 0.0,
                    cost_completion_tokens=row["cost_completion_tokens"] or 0.0,
                    providers=row["providers"],
                    created=row["created"],
                    updated=row["updated"],
                )
            )
        return routers

    async def get_all_aliases(self) -> dict[str, str]:
        aliases_query = select(RouterAliasTable.router_id.label("router_id"), RouterAliasTable.value)
        aliases_result = await self.postgres_session.execute(aliases_query)
        aliases = {}
        for row in aliases_result.all():
            if row.router_id not in aliases:
                aliases[row.router_id] = []
            aliases[row.router_id].append(row.value)
        return aliases
