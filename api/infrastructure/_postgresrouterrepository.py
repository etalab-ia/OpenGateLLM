from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.router import RouterRepository
from api.domain.router.entities import Model, ModelCosts, ModelType, Router, RouterLoadBalancingStrategy
from api.domain.userinfo.entities import UserInfo
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable
from api.utils.exceptions import ModelNotFoundException, RouterNotFoundException


class PostgresRouterRepository(RouterRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_routers(self, router_id: int | None, name: str | None) -> list[Router]:
        """
        Get model router with optional filtering.

        Args:
            postgres_session(AsyncSession): Database postgres_session
            router_id(Optional[int]): Optional router ID to filter by
            name(Optional[str]): Optional router name or alias to filter by
        Returns:
            List of model router schemas
        """
        provider_count_subquery = (
            select(func.count(ProviderTable.id)).where(ProviderTable.router_id == RouterTable.id).correlate(RouterTable).scalar_subquery()
        )

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

        if router_id is not None:
            query = query.where(RouterTable.id == router_id)

        result = await self.postgres_session.execute(query)
        router_results = [row._asdict() for row in result.all()]
        if router_id is not None and len(router_results) == 0:
            raise RouterNotFoundException()

        aliases_query = select(RouterAliasTable.router_id.label("router_id"), RouterAliasTable.value)
        if router_id is not None:
            aliases_query = aliases_query.where(RouterAliasTable.router_id == router_id)

        aliases_result = await self.postgres_session.execute(aliases_query)
        aliases = {}
        for row in aliases_result.all():
            if row.router_id not in aliases:
                aliases[row.router_id] = []
            aliases[row.router_id].append(row.value)

        routers = []
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
        # Filter routers by name if provided
        if name is not None:
            routers = [router for router in routers if router.name == name or any(alias == name for alias in router.aliases)]
            if not routers:
                raise RouterNotFoundException()

        return routers

    async def get_all_models(self, routers: list[Router], name: str | None, user_info: UserInfo) -> list[Model]:
        try:
            routers = await self.get_routers(router_id=None, name=name)
        except RouterNotFoundException:
            raise ModelNotFoundException()

        models = []
        for router in routers:
            # skip model if user has no access to it
            has_access = True
            for limit in user_info.limits:
                if limit.router == router.id and limit.value == 0:
                    has_access = False
                    break

            if not has_access:
                if name is not None:
                    raise ModelNotFoundException()
                continue

            if router.providers == 0:
                if name is not None:
                    raise ModelNotFoundException()
                continue

            # get organization name as owned by
            query = (
                select(OrganizationTable.name.label("owned_by"))
                .join(UserTable, UserTable.organization_id == OrganizationTable.id)
                .where(UserTable.id == router.user_id)
            )
            result = await self.postgres_session.execute(query)
            owned_by = result.scalar_one_or_none()
            owned_by = owned_by if owned_by else self.app_title

            models.append(
                Model(
                    id=router.name,
                    type=router.type,
                    owned_by=owned_by,
                    aliases=router.aliases,
                    created=router.created,
                    max_context_length=router.max_context_length,
                    costs=ModelCosts(prompt_tokens=router.cost_prompt_tokens, completion_tokens=router.cost_completion_tokens),
                )
            )

        return models
