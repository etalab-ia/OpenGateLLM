from sqlalchemy import Integer, cast, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.router import RouterRepository
from api.domain.router._routerrepository import RouterNameAlreadyExists
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable


class PostgresRouterRepository(RouterRepository):
    def __init__(self, postgres_session: AsyncSession, app_title: str):
        self.queuing_enabled = False
        self.postgres_session = postgres_session
        self.app_title = app_title
        self.master_user_id = 0

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

        aliases = await self.get_aliases_by_router_id()

        for row in router_results:
            user_id = self.master_user_id if row["user_id"] is None else row["user_id"]
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

    async def get_aliases_by_router_id(self) -> dict[str, list[str]]:
        aliases_query = select(RouterAliasTable.router_id.label("router_id"), RouterAliasTable.value)
        aliases_result = await self.postgres_session.execute(aliases_query)
        aliases = {}
        for row in aliases_result.all():
            if row.router_id not in aliases:
                aliases[row.router_id] = []
            aliases[row.router_id].append(row.value)
        return aliases

    async def create_router(
        self,
        name: str,
        router_type: ModelType,
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
    ) -> Router | RouterNameAlreadyExists:
        db_user_id = None if user_id == self.master_user_id else user_id
        try:
            query = (
                insert(RouterTable)
                .values(
                    user_id=db_user_id,
                    name=name,
                    type=router_type.value,
                    load_balancing_strategy=load_balancing_strategy.value,
                    cost_prompt_tokens=cost_prompt_tokens,
                    cost_completion_tokens=cost_completion_tokens,
                )
                .returning(
                    RouterTable.id,
                    RouterTable.name,
                    RouterTable.user_id,
                    RouterTable.type,
                    RouterTable.load_balancing_strategy,
                    RouterTable.cost_prompt_tokens,
                    RouterTable.cost_completion_tokens,
                    cast(func.extract("epoch", RouterTable.created), Integer).label("created"),
                    cast(func.extract("epoch", RouterTable.updated), Integer).label("updated"),
                )
            )
            result = await self.postgres_session.execute(query)
            row = result.one()
        except IntegrityError:
            return RouterNameAlreadyExists(name=name)

        return Router(
            id=row.id,
            name=row.name,
            user_id=user_id,
            type=ModelType(row.type),
            aliases=[],
            load_balancing_strategy=RouterLoadBalancingStrategy(row.load_balancing_strategy),
            vector_size=None,
            max_context_length=None,
            cost_prompt_tokens=row.cost_prompt_tokens or 0.0,
            cost_completion_tokens=row.cost_completion_tokens or 0.0,
            providers=0,
            created=row.created,
            updated=row.updated,
        )

    async def get_aliases(self, filtered_aliases: list[str] | None = None) -> list[str]:
        query = select(RouterAliasTable.value)
        if filtered_aliases is not None:
            query = query.where(RouterAliasTable.value.in_(filtered_aliases))
        result = await self.postgres_session.execute(query)
        return [row[0] for row in result.all()]

    async def insert_aliases(self, aliases: list[str], router_id: int) -> list[str]:
        aliases_by_id = [{"value": alias, "router_id": router_id} for alias in aliases]
        await self.postgres_session.execute(insert(RouterAliasTable), aliases_by_id)
        return aliases
