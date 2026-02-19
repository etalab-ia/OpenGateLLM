from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.model.entities import Metric
from api.domain.provider import ProviderRepository
from api.domain.provider.entities import Provider, ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import ProviderAlreadyExistsError
from api.sql.models import Provider as ProviderTable


class PostgresProviderRepository(ProviderRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

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
            return Provider(
                router_id=row.router_id,
                user_id=row.user_id,
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
            )
        except IntegrityError as e:
            if "unique_provider_router_id_url_model_name" in str(e.orig):
                return ProviderAlreadyExistsError(model_name=model_name, url=url, router_id=router_id)
            raise
