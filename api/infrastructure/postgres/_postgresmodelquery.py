from sqlalchemy import Integer, Select, cast, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.model import ModelQuery
from api.domain.model.entities import ModelCosts, ModelType
from api.domain.model.errors import ModelNotFoundError
from api.domain.model.views import ModelView
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable


def _unix_timestamp(column):
    return cast(func.extract("epoch", column), Integer)


class PostgresModelQuery(ModelQuery):
    def __init__(self, postgres_session: AsyncSession, app_title: str):
        self.postgres_session = postgres_session
        self.app_title = app_title

    async def get_models(self) -> list[ModelView]:
        statement = self._build_statement().order_by(RouterTable.id)

        result = await self.postgres_session.execute(statement=statement)

        return [self._row_to_view(row) for row in result.all()]

    async def get_model_by_name_or_alias(self, name: str) -> ModelView | ModelNotFoundError:
        alias_matches = (
            select(literal(1)).where(RouterAliasTable.router_id == RouterTable.id, RouterAliasTable.value == name).correlate(RouterTable).exists()
        )
        statement = self._build_statement().where(or_(RouterTable.name == name, alias_matches)).order_by(RouterTable.id).limit(1)

        result = await self.postgres_session.execute(statement=statement)
        row = result.one_or_none()
        if row is None:
            return ModelNotFoundError(name=name)

        return self._row_to_view(row)

    def _build_statement(self) -> Select:
        aliases_subquery = (
            select(func.coalesce(func.array_agg(RouterAliasTable.value), text("'{}'::text[]")))
            .where(RouterAliasTable.router_id == RouterTable.id)
            .correlate(RouterTable)
            .scalar_subquery()
            .label("aliases")
        )

        # capabilities live on provider: the models API exposes the ones of the first provider of the router
        max_context_length_subquery = (
            select(ProviderTable.max_context_length)
            .where(ProviderTable.router_id == RouterTable.id)
            .correlate(RouterTable)
            .order_by(ProviderTable.id)
            .limit(1)
            .scalar_subquery()
            .label("max_context_length")
        )

        has_providers = select(literal(1)).where(ProviderTable.router_id == RouterTable.id).correlate(RouterTable).exists()

        return (
            select(
                RouterTable.id.label("router_id"),
                RouterTable.name.label("id"),
                RouterTable.type,
                RouterTable.cost_prompt_tokens,
                RouterTable.cost_completion_tokens,
                aliases_subquery,
                max_context_length_subquery,
                func.coalesce(OrganizationTable.name, self.app_title).label("owned_by"),
                _unix_timestamp(RouterTable.created).label("created"),
            )
            .select_from(RouterTable)
            .outerjoin(UserTable, UserTable.id == RouterTable.user_id)
            .outerjoin(OrganizationTable, OrganizationTable.id == UserTable.organization_id)
            .where(has_providers)
        )

    @staticmethod
    def _row_to_view(row) -> ModelView:
        return ModelView(
            router_id=row.router_id,
            id=row.id,
            type=ModelType(row.type),
            aliases=row.aliases,
            created=row.created,
            owned_by=row.owned_by,
            max_context_length=row.max_context_length,
            costs=ModelCosts(prompt_tokens=row.cost_prompt_tokens or 0.0, completion_tokens=row.cost_completion_tokens or 0.0),
        )
