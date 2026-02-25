from sqlalchemy import Integer, Select, asc, cast, desc, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key.entities import MASTER_USER_ID
from api.domain.model import ModelType as RouterType
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterPage, RouterSortField, SortOrder
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable


class PostgresRouterRepository(RouterRepository):
    def __init__(self, postgres_session: AsyncSession, app_title: str):
        self.postgres_session = postgres_session
        self.app_title = app_title

    @staticmethod
    def _select_routers_with_provider_stats() -> Select:
        provider_count = func.count(ProviderTable.id).over(partition_by=RouterTable.id).label("providers")
        return select(
            RouterTable.id,
            RouterTable.name,
            RouterTable.user_id,
            RouterTable.type,
            RouterTable.load_balancing_strategy,
            RouterTable.cost_prompt_tokens,
            RouterTable.cost_completion_tokens,
            ProviderTable.max_context_length,
            ProviderTable.vector_size,
            provider_count,
            cast(func.extract("epoch", RouterTable.created), Integer).label("created"),
            cast(func.extract("epoch", RouterTable.updated), Integer).label("updated"),
        ).join(ProviderTable, ProviderTable.router_id == RouterTable.id, isouter=True)

    @staticmethod
    def _row_to_router_with_aliases(row, aliases: list[str]) -> Router:
        user_id = MASTER_USER_ID if row.user_id is None else row.user_id
        return Router(
            id=row.id,
            name=row.name,
            user_id=user_id,
            type=RouterType(row.type),
            aliases=aliases,
            load_balancing_strategy=RouterLoadBalancingStrategy(row.load_balancing_strategy),
            vector_size=row.vector_size,
            max_context_length=row.max_context_length,
            cost_prompt_tokens=row.cost_prompt_tokens or 0.0,
            cost_completion_tokens=row.cost_completion_tokens or 0.0,
            providers=row.providers,
            created=row.created,
            updated=row.updated,
        )

    async def get_aliases_by_router_id(self, router_id: int) -> list[str]:
        query = select(RouterAliasTable.value).where(RouterAliasTable.router_id == router_id)
        result = await self.postgres_session.execute(query)
        return [row[0] for row in result.all()]

    async def get_router_by_id(self, router_id: int) -> Router | None:
        query = self._select_routers_with_provider_stats().where(RouterTable.id == router_id).limit(1)
        result = await self.postgres_session.execute(query)
        row = result.one_or_none()
        if row is None:
            return None
        aliases = await self.get_aliases_by_router_id(router_id)
        return self._row_to_router_with_aliases(row, aliases)

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
        query = self._select_routers_with_provider_stats().distinct(RouterTable.id).order_by(RouterTable.id, ProviderTable.id)
        result = await self.postgres_session.execute(query)
        aliases_by_router = await self.get_aliases_grouped_by_router()
        return [self._row_to_router_with_aliases(row, aliases_by_router.get(row.id, [])) for row in result.all()]

    async def get_routers_page(
        self,
        limit: int,
        offset: int,
        sort_by: RouterSortField = RouterSortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> RouterPage:
        distinct_routers = (self._select_routers_with_provider_stats().distinct(RouterTable.id).order_by(RouterTable.id, ProviderTable.id)).subquery()

        sort_column = distinct_routers.c[sort_by.value]
        sort_order_clause = asc(sort_column) if sort_order == SortOrder.ASC else desc(sort_column)

        routers_query = select(distinct_routers, func.count().over().label("total")).order_by(sort_order_clause).limit(limit).offset(offset)
        result = await self.postgres_session.execute(routers_query)

        rows = result.all()
        total = rows[0].total if rows else 0
        router_ids = [row.id for row in rows]
        aliases_by_router = await self.get_aliases_grouped_by_router(router_ids)
        routers = [self._row_to_router_with_aliases(row, aliases_by_router.get(row.id, [])) for row in rows]

        return RouterPage(total=total, data=routers)

    async def get_aliases_grouped_by_router(self, router_ids: list[int] | None = None) -> dict[int, list[str]]:
        query = select(RouterAliasTable.router_id, RouterAliasTable.value)
        if router_ids is not None:
            query = query.where(RouterAliasTable.router_id.in_(router_ids))
        result = await self.postgres_session.execute(query)
        aliases: dict[int, list[str]] = {}
        for row in result.all():
            aliases.setdefault(row.router_id, []).append(row.value)
        return aliases

    async def create_router(
        self,
        name: str,
        router_type: RouterType,
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
        aliases: list[str] | None = None,
    ) -> Router | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError:
        db_user_id = None if user_id == MASTER_USER_ID else user_id
        aliases = aliases or []

        try:
            async with self.postgres_session.begin_nested():
                insert_router_query = (
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
                result = await self.postgres_session.execute(insert_router_query)
                row = result.one()

                if aliases:
                    aliases_to_insert = [{"value": alias, "router_id": row.id} for alias in aliases]
                    await self.postgres_session.execute(insert(RouterAliasTable), aliases_to_insert)

        except IntegrityError as e:
            if "router_name_key" in str(e.orig):
                return RouterNameAlreadyExistsError(name=name)
            if "router_alias_value_key" in str(e.orig):
                if isinstance(e.params, tuple):
                    duplicate_aliases = [e.params[1]]
                else:
                    duplicate_aliases = [params[1] for params in e.params]
                return RouterAliasAlreadyExistsError(aliases=duplicate_aliases)
            raise

        return Router(
            id=row.id,
            name=row.name,
            user_id=user_id,
            type=RouterType(row.type),
            aliases=aliases,
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
