from sqlalchemy import asc, delete, desc, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain import SortOrder
from api.domain.key.entities import MASTER_USER_ID
from api.domain.model.entities import Metric
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider, ProviderCarbonFootprintZone, ProviderPage, ProviderSortField, ProviderType
from api.domain.provider.errors import ProviderAlreadyExistsError
from api.sql.models import Provider as ProviderTable


class PostgresProviderRepository(ProviderRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_providers_page(
        self, router_id: int | None, limit: int, offset: int, sort_by: ProviderSortField = ProviderSortField.ID, sort_order: SortOrder = SortOrder.ASC
    ) -> ProviderPage:
        select_query = select(ProviderTable)
        count_query = select(func.count()).select_from(ProviderTable)

        if router_id is not None:
            select_query = select_query.where(ProviderTable.router_id == router_id)
            count_query = count_query.where(ProviderTable.router_id == router_id)

        total = (await self.postgres_session.execute(count_query)).scalar_one()
        sort_column = getattr(ProviderTable, sort_by.value)
        sort_order_clause = asc(sort_column) if sort_order == SortOrder.ASC else desc(sort_column)

        providers_query = select_query.order_by(sort_order_clause).limit(limit).offset(offset)

        rows = (await self.postgres_session.execute(providers_query)).scalars().all()

        return ProviderPage(total=total, data=[self._row_to_provider(row) for row in rows])

    async def get_one_provider(self, provider_id: int) -> Provider | None:
        select_query = select(ProviderTable).where(ProviderTable.id == provider_id)

        result = await self.postgres_session.execute(select_query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._row_to_provider(row)

    @staticmethod
    def _row_to_provider(row) -> Provider:
        return Provider(
            router_id=row.router_id,
            user_id=MASTER_USER_ID if row.user_id is None else row.user_id,
            type=row.type,
            url=row.url,
            key=row.key,
            timeout=row.timeout,
            model_name=row.model_name,
            model_hosting_zone=row.model_hosting_zone,
            model_total_params=row.model_total_params,
            model_active_params=row.model_active_params,
            qos_metric=row.qos_metric,
            qos_limit=row.qos_limit,
            max_context_length=row.max_context_length,
            vector_size=row.vector_size,
            id=row.id,
            created=int(row.created.timestamp()),
            updated=int(row.updated.timestamp()),
        )

    async def create_provider(
        self,
        router_id: int,
        user_id: int,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
        model_hosting_zone: ProviderCarbonFootprintZone,
        model_total_params: int,
        model_active_params: int,
        qos_metric: Metric | None,
        qos_limit: float | None,
        vector_size: int,
        max_context_length: int,
    ) -> Provider | ProviderAlreadyExistsError:
        try:
            qos_metric = qos_metric.value if qos_metric is not None else None
            query = (
                insert(ProviderTable)
                .values(
                    router_id=router_id,
                    user_id=user_id,
                    type=provider_type.value,
                    url=url,
                    key=key,
                    timeout=timeout,
                    model_name=model_name,
                    model_hosting_zone=model_hosting_zone,
                    model_total_params=model_total_params,
                    model_active_params=model_active_params,
                    qos_metric=qos_metric,
                    qos_limit=qos_limit,
                    max_context_length=max_context_length,
                    vector_size=vector_size,
                )
                .returning(ProviderTable)
            )
            result = await self.postgres_session.execute(query)
            row = result.scalar_one()
            return self._row_to_provider(row)
        except IntegrityError as e:
            if "unique_provider_router_id_url_model_name" in str(e.orig):
                return ProviderAlreadyExistsError(model_name=model_name, url=url, router_id=router_id)
            raise

    async def delete_provider(self, provider_id: int) -> Provider | None:
        select_query = select(ProviderTable).where(ProviderTable.id == provider_id)
        result = await self.postgres_session.execute(select_query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        delete_query = delete(ProviderTable).where(ProviderTable.id == provider_id)
        await self.postgres_session.execute(delete_query)
        return self._row_to_provider(row)
