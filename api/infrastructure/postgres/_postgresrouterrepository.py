from collections.abc import Sequence

from sqlalchemy import Row, Select, asc, delete, desc, func, insert, literal, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from api.domain import SortField, SortOrder
from api.domain.provider.entities import Provider
from api.domain.router import RouterRepository
from api.domain.router.entities import Router, RouterPage, RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.infrastructure.postgres._providermapping import row_to_provider
from api.infrastructure.postgres.decorators import with_lock
from api.infrastructure.postgres.models import Router as RouterTable
from api.infrastructure.postgres.models import RouterAlias as RouterAliasTable


class PostgresRouterRepository(RouterRepository):
    # every column but load_balancing_strategy, so that a later release can drop it
    _RETURNING_COLUMNS = (
        RouterTable.id,
        RouterTable.name,
        RouterTable.user_id,
        RouterTable.type,
        RouterTable.qos_retries_before_reject,
        RouterTable.cost_prompt_tokens,
        RouterTable.cost_completion_tokens,
        RouterTable.created,
        RouterTable.updated,
    )

    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    @staticmethod
    def _select_routers_statement() -> Select:
        return select(RouterTable).options(
            joinedload(RouterTable.provider),
            joinedload(RouterTable.alias),
            # no longer read, so that a later release can drop the column
            defer(RouterTable.load_balancing_strategy, raiseload=True),
        )

    async def _fetch_rows(self, query: Select) -> Sequence[Row]:
        result = await self.postgres_session.execute(query)

        return result.unique().all()

    @classmethod
    def _row_to_router_with_providers(cls, row: Row) -> Router:
        return cls._row_to_router(
            row=row.Router,
            aliases=[alias.value for alias in row.Router.alias],
            providers=[row_to_provider(provider) for provider in row.Router.provider],
        )

    @staticmethod
    def _row_to_router(row, aliases: list[str], providers: list[Provider]) -> Router:
        return Router(
            id=row.id,
            name=row.name,
            user_id=row.user_id,
            type=RouterType(row.type),
            aliases=aliases,
            qos_retries_before_reject=row.qos_retries_before_reject,
            cost_prompt_tokens=row.cost_prompt_tokens or 0.0,
            cost_completion_tokens=row.cost_completion_tokens or 0.0,
            providers=providers,
            created=row.created,
            updated=row.updated,
        )

    async def get_router_by_id(self, router_id: int) -> Router | RouterNotFoundError:
        query = self._select_routers_statement().where(RouterTable.id == router_id)
        rows = await self._fetch_rows(query)
        if not rows:
            return RouterNotFoundError(id=router_id)

        return self._row_to_router_with_providers(rows[0])

    async def get_router_by_name_or_alias(self, name_or_alias: str) -> Router | RouterNotFoundError:
        alias_matches = (
            select(literal(1))
            .where(RouterAliasTable.router_id == RouterTable.id, RouterAliasTable.value == name_or_alias)
            .correlate(RouterTable)
            .exists()
        )
        query = self._select_routers_statement().where(or_(RouterTable.name == name_or_alias, alias_matches)).order_by(RouterTable.id).limit(1)
        rows = await self._fetch_rows(query)
        if not rows:
            return RouterNotFoundError(name=name_or_alias)

        return self._row_to_router_with_providers(rows[0])

    async def get_all_routers(self) -> list[Router]:
        query = self._select_routers_statement().order_by(RouterTable.id)
        rows = await self._fetch_rows(query)

        return [self._row_to_router_with_providers(row) for row in rows]

    async def get_routers_page(
        self,
        limit: int,
        offset: int,
        sort_by: SortField = SortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> RouterPage:
        sort_column = getattr(RouterTable, sort_by.value)
        sort_order_clause = asc(sort_column) if sort_order == SortOrder.ASC else desc(sort_column)

        routers_query = (
            self._select_routers_statement().add_columns(func.count().over().label("total")).order_by(sort_order_clause).limit(limit).offset(offset)
        )
        rows = await self._fetch_rows(routers_query)
        total = rows[0].total if rows else (await self.postgres_session.execute(select(func.count()).select_from(RouterTable))).scalar_one()

        return RouterPage(total=total, data=[self._row_to_router_with_providers(row) for row in rows])

    @with_lock(namespace="router", key="name")
    async def create_router(
        self,
        name: str,
        router_type: RouterType,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
        aliases: list[str] | None = None,
        qos_retries_before_reject: int | None = None,
    ) -> Router | RouterNameAlreadyExistsError | RouterAliasAlreadyExistsError:
        aliases = aliases or []

        try:
            insert_router_query = (
                insert(RouterTable)
                .values(
                    user_id=user_id,
                    name=name,
                    type=router_type.value,
                    qos_retries_before_reject=qos_retries_before_reject,
                    cost_prompt_tokens=cost_prompt_tokens,
                    cost_completion_tokens=cost_completion_tokens,
                )
                .returning(*self._RETURNING_COLUMNS)
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

        return self._row_to_router(row=row, aliases=aliases, providers=[])

    async def get_aliases(self, filtered_aliases: list[str] | None = None) -> list[str]:
        query = select(RouterAliasTable.value)
        if filtered_aliases is not None:
            query = query.where(RouterAliasTable.value.in_(filtered_aliases))
        result = await self.postgres_session.execute(query)
        return [row[0] for row in result.all()]

    @with_lock(namespace="router", key="router_id")
    async def delete_router(self, router_id: int) -> Router | RouterNotFoundError:
        # retrieve the router first to return aliases
        result = await self.get_router_by_id(router_id)
        match result:
            case RouterNotFoundError():
                return RouterNotFoundError(id=router_id)
            case Router() as router:
                pass

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
                    qos_retries_before_reject=router.qos_retries_before_reject,
                    cost_prompt_tokens=router.cost_prompt_tokens,
                    cost_completion_tokens=router.cost_completion_tokens,
                )
                .returning(*self._RETURNING_COLUMNS)
            )
            result = await self.postgres_session.execute(update_query)
            row = result.one()

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

        return self._row_to_router(row=row, aliases=router.aliases, providers=router.providers)

    async def get_router_ids_by_user_id(self, user_id: int) -> list[int]:
        result = await self.postgres_session.execute(statement=select(RouterTable.id).where(RouterTable.user_id == user_id))
        return list(result.scalars().all())
