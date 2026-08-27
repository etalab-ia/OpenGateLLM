from sqlalchemy import Integer, Select, asc, cast, delete, desc, func, insert, literal, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain import SortField, SortOrder
from api.domain.model.entities import ModelType as RouterType
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterLoadBalancingStrategy, RouterPage
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.infrastructure.postgres._pagination import fetch_page_with_total
from api.infrastructure.postgres.decorators import with_lock
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable


def _unix_timestamp(column):
    return cast(func.extract("epoch", column), Integer)


class PostgresRouterRepository(RouterRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _select_providers_statement() -> Select:
        return (
            select(func.count(ProviderTable.id))
            .where(ProviderTable.router_id == RouterTable.id)
            .correlate(RouterTable)
            .scalar_subquery()
            .label("providers")
        )

    @staticmethod
    def _select_aliases_statement() -> list[str]:
        return (
            select(func.coalesce(func.array_agg(RouterAliasTable.value), text("'{}'::text[]")))
            .where(RouterAliasTable.router_id == RouterTable.id)
            .correlate(RouterTable)
            .scalar_subquery()
            .label("aliases")
        )

    @staticmethod
    def _select_all_routers_statement() -> Select:
        return select(
            RouterTable.id,
            RouterTable.name,
            RouterTable.user_id,
            RouterTable.type,
            RouterTable.load_balancing_strategy,
            RouterTable.cost_prompt_tokens,
            RouterTable.cost_completion_tokens,
            PostgresRouterRepository._select_providers_statement(),
            PostgresRouterRepository._select_aliases_statement(),
            _unix_timestamp(RouterTable.created).label("created"),
            _unix_timestamp(RouterTable.updated).label("updated"),
        )

    @staticmethod
    def _row_to_router_with_aliases(row, aliases: list[str] | None = None) -> Router:
        return Router(
            id=row.id,
            name=row.name,
            user_id=row.user_id,
            type=RouterType(row.type),
            aliases=row.aliases if aliases is None else aliases,
            load_balancing_strategy=RouterLoadBalancingStrategy(row.load_balancing_strategy),
            cost_prompt_tokens=row.cost_prompt_tokens or 0.0,
            cost_completion_tokens=row.cost_completion_tokens or 0.0,
            providers=row.providers,
            created=row.created,
            updated=row.updated,
        )

    async def get_router_by_id(self, router_id: int) -> Router | RouterNotFoundError:
        query = self._select_all_routers_statement().where(RouterTable.id == router_id)
        result = await self.postgres_session.execute(query)
        row = result.one_or_none()
        if row is None:
            return RouterNotFoundError(id=router_id)

        return self._row_to_router_with_aliases(row)

    async def get_router_by_name_or_alias(self, name_or_alias: str) -> Router | RouterNotFoundError:
        alias_matches = (
            select(literal(1))
            .where(RouterAliasTable.router_id == RouterTable.id, RouterAliasTable.value == name_or_alias)
            .correlate(RouterTable)
            .exists()
        )
        query = self._select_all_routers_statement().where(or_(RouterTable.name == name_or_alias, alias_matches)).order_by(RouterTable.id).limit(1)
        result = await self.postgres_session.execute(query)
        row = result.one_or_none()
        if row is None:
            return RouterNotFoundError(name=name_or_alias)

        return self._row_to_router_with_aliases(row)

    async def get_all_routers(self) -> list[Router]:
        query = self._select_all_routers_statement().order_by(RouterTable.id)
        result = await self.postgres_session.execute(query)

        return [self._row_to_router_with_aliases(row) for row in result.all()]

    async def get_routers_page(
        self,
        limit: int,
        offset: int,
        sort_by: SortField = SortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> RouterPage:
        routers = self._select_all_routers_statement().subquery()

        sort_column = routers.c[sort_by.value]
        sort_order_clause = asc(sort_column) if sort_order == SortOrder.ASC else desc(sort_column)

        routers_query = select(routers, func.count().over().label("total")).order_by(sort_order_clause).limit(limit).offset(offset)
        count_query = select(func.count()).select_from(RouterTable)
        rows, total = await fetch_page_with_total(self.postgres_session, routers_query, count_query)

        return RouterPage(total=total, data=[self._row_to_router_with_aliases(row) for row in rows])

    @with_lock(namespace="router", key="name")
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
        aliases = aliases or []

        try:
            insert_router_query = (
                insert(RouterTable)
                .values(
                    user_id=user_id,
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
                    cast(literal(0), Integer).label("providers"),
                    _unix_timestamp(RouterTable.created).label("created"),
                    _unix_timestamp(RouterTable.updated).label("updated"),
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

        return self._row_to_router_with_aliases(row=row, aliases=aliases)

    async def get_aliases(self, filtered_aliases: list[str] | None = None) -> list[str]:
        query = select(RouterAliasTable.value)
        if filtered_aliases is not None:
            query = query.where(RouterAliasTable.value.in_(filtered_aliases))
        result = await self.postgres_session.execute(query)
        return [row[0] for row in result.all()]

    @with_lock(namespace="router", key="router_id")
    async def delete_router(self, router_id: int) -> Router | RouterNotFoundError:
        router = await self.get_router_by_id(router_id)
        if isinstance(router, RouterNotFoundError):
            return RouterNotFoundError(id=router_id)
        await self.postgres_session.execute(delete(RouterTable).where(RouterTable.id == router_id))
        return router

    async def delete_all_routers(self) -> list[Router]:
        routers = await self.get_all_routers()
        await self.postgres_session.execute(delete(RouterTable).where(RouterTable.id.in_([router.id for router in routers])))
        return routers

    async def update_router(self, router: Router) -> Router | RouterNameAlreadyExistsError:
        try:
            update_query = (
                update(RouterTable)
                .where(RouterTable.id == router.id)
                .values(
                    user_id=router.user_id,
                    name=router.name,
                    type=router.type.value,
                    load_balancing_strategy=router.load_balancing_strategy.value,
                    cost_prompt_tokens=router.cost_prompt_tokens,
                    cost_completion_tokens=router.cost_completion_tokens,
                )
                .returning(
                    RouterTable.id,
                    RouterTable.name,
                    RouterTable.user_id,
                    RouterTable.type,
                    RouterTable.load_balancing_strategy,
                    RouterTable.cost_prompt_tokens,
                    RouterTable.cost_completion_tokens,
                    _unix_timestamp(RouterTable.created).label("created"),
                    _unix_timestamp(RouterTable.updated).label("updated"),
                )
            )
            result = await self.postgres_session.execute(update_query)
            row = result.one()

            if router.aliases is not None:
                await self.postgres_session.execute(delete(RouterAliasTable).where(RouterAliasTable.router_id == router.id))
                if router.aliases:
                    await self.postgres_session.execute(
                        insert(RouterAliasTable),
                        [{"value": alias, "router_id": router.id} for alias in router.aliases],
                    )
        except IntegrityError as e:
            if "router_name_key" in str(e.orig):
                return RouterNameAlreadyExistsError(name=router.name)
            raise

        return Router(
            id=row.id,
            name=row.name,
            user_id=router.user_id,
            type=RouterType(row.type),
            aliases=router.aliases,
            load_balancing_strategy=RouterLoadBalancingStrategy(row.load_balancing_strategy),
            cost_prompt_tokens=row.cost_prompt_tokens or 0.0,
            cost_completion_tokens=row.cost_completion_tokens or 0.0,
            providers=router.providers,
            created=row.created,
            updated=row.updated,
        )

    async def get_router_ids_by_user_id(self, user_id: int) -> list[int]:
        result = await self.postgres_session.execute(statement=select(RouterTable.id).where(RouterTable.user_id == user_id))
        return list(result.scalars().all())
