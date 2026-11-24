from api.domain.provider.entities import HostingZone, Provider
from api.infrastructure.postgres.models import Provider as ProviderTable


def row_to_provider(row: ProviderTable) -> Provider:
    return Provider(
        router_id=row.router_id,
        user_id=row.user_id,
        type=row.type,
        url=row.url,
        key=row.key,
        timeout=row.timeout,
        qos_limit=row.qos_limit,
        model_name=row.model_name,
        model_hosting_zone=HostingZone[row.model_hosting_zone],
        model_total_params=row.model_total_params,
        model_active_params=row.model_active_params,
        max_context_length=row.max_context_length,
        vector_size=row.vector_size,
        id=row.id,
        created=row.created,
        updated=row.updated,
    )
