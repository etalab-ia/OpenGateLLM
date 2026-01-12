from sqlalchemy import Integer, cast, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.router import RouterRepository
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable
from api.tasks import add_model_queue_to_running_worker
from api.utils.exceptions import RouterAliasAlreadyExistsException, RouterAlreadyExistsException
from api.utils.variables import PREFIX__CELERY_QUEUE_ROUTING


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

        aliases = await self.get_all_aliases()

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

    async def get_all_aliases(self) -> dict[str, str]:
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
        type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: str,
    ) -> list[Router]:
        user_id = None if user_id == 0 else user_id  # 0 corresponds to master user ID
        try:
            query = (
                insert(RouterTable)
                .values(
                    user_id=user_id,
                    name=name,
                    type=type.value,
                    load_balancing_strategy=load_balancing_strategy.value,
                    cost_prompt_tokens=cost_prompt_tokens,
                    cost_completion_tokens=cost_completion_tokens,
                )
                .returning(RouterTable.id)
            )
            result = await self.postgres_session.execute(query)
            router_id = result.scalar_one()
        except IntegrityError:
            await self.postgres_session.rollback()
            raise RouterAlreadyExistsException()

        # Check names integrity
        check_names = [name, *aliases]
        query = select(RouterAliasTable.value).where(RouterAliasTable.value.in_(check_names))
        result = await self.postgres_session.execute(query)
        existing_aliases = [alias[0] for alias in result.all()]
        if existing_aliases:
            await self.postgres_session.rollback()
            raise RouterAliasAlreadyExistsException()

        # Add aliases
        if aliases:
            for alias in aliases:
                query = insert(RouterAliasTable).values(value=alias, router_id=router_id)
                await self.postgres_session.execute(query)

        await self.postgres_session.commit()

        if self.queuing_enabled:
            add_model_queue_to_running_worker(queue_name=f"{PREFIX__CELERY_QUEUE_ROUTING}.{router_id}")

        return router_id
