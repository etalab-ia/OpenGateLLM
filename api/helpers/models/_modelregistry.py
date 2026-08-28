from contextvars import ContextVar
import logging
from typing import Literal

from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import Integer, and_, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider as ModelProvider
from api.domain.provider.entities import Provider
from api.schemas.admin.routers import Router, RouterLoadBalancingStrategy
from api.schemas.core.context import RequestContext
from api.schemas.core.models import Metric
from api.schemas.me.info import UserInfo
from api.schemas.models import Model, ModelCosts, ModelType
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable
from api.utils.exceptions import (
    InsufficientBudgetException,
    ModelNotFoundException,
    ProviderNotFoundException,
    RouterNotFoundException,
    WrongModelTypeException,
)
from api.utils.routing import apply_routing_with_queuing, apply_routing_without_queuing
from api.utils.variables import PREFIX__CELERY_QUEUE_ROUTING, EndpointRoute

MASTER_ID = 0
logger = logging.getLogger(__name__)


class ModelRegistry:
    ENDPOINT_MODEL_TYPE_TABLE = {
        EndpointRoute.AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        EndpointRoute.CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        EndpointRoute.EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        EndpointRoute.OCR: [ModelType.IMAGE_TO_TEXT],
        EndpointRoute.RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

    def __init__(
        self,
        app_title: str,
        queuing_enabled: bool,
        max_priority: int,
        max_retries: int,
        retry_countdown: int,
    ) -> None:
        self.app_title = app_title
        self.queuing_enabled = queuing_enabled
        self.max_priority = max_priority
        self.max_retries = max_retries
        self.retry_countdown = retry_countdown

    @staticmethod
    async def get_routers(
        router_id: int | None,
        name: str | None,
        postgres_session: AsyncSession,
        offset: int | None = None,
        limit: int | None = None,
        order_by: Literal["id", "name", "created"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Router]:
        """
        Get model routers with optional filtering, pagination and ordering.

        Args:
            postgres_session (AsyncSession): Database postgres_session.
            router_id (Optional[int]): Optional router ID to filter by.
            name (Optional[str]): Optional router name or alias to filter by.
            offset (int | None): Pagination offset (default: None).
            limit (int | None): Maximum number of routers to return (default: None).
            order_by (Literal["id", "name", "created"]): Field to order results by (default: "id").
            order_direction (Literal["asc", "desc"]): Order direction (default: "asc").

        Returns:
            List[Router]: List of model router schemas.

        Raises:
            RouterNotFoundException: If a specific router_id or name is provided and no matching router is found.
        """

        provider_count_subquery = (
            select(func.count(ProviderTable.id)).where(ProviderTable.router_id == RouterTable.id).correlate(RouterTable).scalar_subquery()
        )

        first_provider_subquery = select(
            ProviderTable.router_id,
            ProviderTable.max_context_length,
            ProviderTable.vector_size,
            func.row_number().over(partition_by=ProviderTable.router_id, order_by=ProviderTable.id).label("rn"),
        ).subquery()

        query = (
            (
                select(
                    RouterTable.id,
                    RouterTable.name,
                    RouterTable.user_id,
                    RouterTable.type,
                    RouterTable.load_balancing_strategy,
                    RouterTable.cost_prompt_tokens,
                    RouterTable.cost_completion_tokens,
                    first_provider_subquery.c.max_context_length,
                    first_provider_subquery.c.vector_size,
                    provider_count_subquery.label("providers"),
                    cast(func.extract("epoch", RouterTable.created), Integer).label("created"),
                    cast(func.extract("epoch", RouterTable.updated), Integer).label("updated"),
                )
                .join(
                    first_provider_subquery,
                    and_(first_provider_subquery.c.router_id == RouterTable.id, first_provider_subquery.c.rn == 1),
                    isouter=True,
                )
                .order_by(text(f"{order_by} {order_direction}"))  # nosemgrep
            )
            .offset(offset=offset)
            .limit(limit=limit)
        )

        if router_id is not None:
            query = query.where(RouterTable.id == router_id)

        result = await postgres_session.execute(query)
        router_results = [row._asdict() for row in result.all()]

        if router_id is not None and len(router_results) == 0:
            raise RouterNotFoundException()

        aliases_query = select(RouterAliasTable.router_id.label("router_id"), RouterAliasTable.value)
        if router_id is not None:
            aliases_query = aliases_query.where(RouterAliasTable.router_id == router_id)

        aliases_result = await postgres_session.execute(aliases_query)
        aliases = {}
        for row in aliases_result.all():
            if row.router_id not in aliases:
                aliases[row.router_id] = []
            aliases[row.router_id].append(row.value)

        routers = []
        for row in router_results:
            user_id = MASTER_ID if row["user_id"] is None else row["user_id"]
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

    @staticmethod
    async def get_providers(
        router_id: int,
        provider_id: int | None,
        postgres_session: AsyncSession,
        offset: int | None = None,
        limit: int | None = None,
        order_by: Literal["id", "name", "created"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> list[Provider]:
        """
        Get a specific model provider.

        Args:
            router_id(int): The model router ID
            provider_id(Optional[int]): Optional provider ID to filter by
            postgres_session: Database postgres_session
            offset (int | None): Pagination offset (default: None).
            limit (int | None): Maximum number of providers to return (default: None).
            order_by (Literal["id", "name", "created"]): Field to order results by (default: "id").
            order_direction (Literal["asc", "desc"]): Order direction (default: "asc").

        Returns:
            The provider schema or None
        """
        query = select(
            ProviderTable.id,
            ProviderTable.router_id,
            ProviderTable.user_id,
            ProviderTable.type,
            ProviderTable.url,
            ProviderTable.key,
            ProviderTable.timeout,
            ProviderTable.model_name,
            ProviderTable.model_hosting_zone,
            ProviderTable.model_total_params,
            ProviderTable.model_active_params,
            ProviderTable.qos_metric,
            ProviderTable.qos_limit,
            ProviderTable.created,
            ProviderTable.updated,
        ).order_by(text(f"{order_by} {order_direction}"))  # nosemgrep
        if offset is not None:
            query = query.offset(offset=offset)
        if limit is not None:
            query = query.limit(limit=limit)

        if router_id is not None:
            query = query.where(ProviderTable.router_id == router_id)

        if provider_id is not None:
            query = query.where(ProviderTable.id == provider_id)

        result = await postgres_session.execute(query)
        rows = result.mappings().all()

        if provider_id is not None and len(rows) == 0:
            raise ProviderNotFoundException()

        providers = []
        for row in rows:
            qos_metric = Metric(row["qos_metric"]) if row["qos_metric"] is not None else None
            user_id = MASTER_ID if row["user_id"] is None else row["user_id"]
            providers.append(
                Provider(
                    id=row["id"],
                    router_id=row["router_id"],
                    user_id=user_id,
                    type=row["type"],
                    url=row["url"],
                    key=row["key"],
                    timeout=row["timeout"],
                    model_name=row["model_name"],
                    model_hosting_zone=row["model_hosting_zone"],
                    model_total_params=row["model_total_params"],
                    model_active_params=row["model_active_params"],
                    qos_metric=qos_metric,
                    qos_limit=row["qos_limit"],
                    created=row["created"],
                    updated=row["updated"],
                )
            )

        return providers

    async def get_models(self, name: str | None, user_info: UserInfo, postgres_session: AsyncSession) -> list[Model]:
        """
        Get models for a user.

        Args:
            name(Optional[str]): Optional model name to filter by
            user_info(UserInfo): User info of the user to apply the limits to the models
            postgres_session(AsyncSession): Database postgres_session
        """

        try:
            routers = await self.get_routers(router_id=None, name=name, postgres_session=postgres_session)
        except RouterNotFoundException:
            raise ModelNotFoundException()

        models = []
        for router in routers:
            # skip model if router has no providers
            if router.providers == 0:
                if name is not None:
                    raise ModelNotFoundException()
                continue

            # skip model if user has no access to it
            router_limit = next((limit for limit in user_info.limits if limit.router_id == router.id), None)
            has_access = router_limit is not None and (router_limit.value is None or router_limit.value > 0)
            if not has_access:
                if name is not None:
                    raise ModelNotFoundException()
                continue

            # get organization name as owned by
            query = (
                select(OrganizationTable.name.label("owned_by"))
                .join(UserTable, UserTable.organization_id == OrganizationTable.id)
                .where(UserTable.id == router.user_id)
            )
            result = await postgres_session.execute(query)
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

    @staticmethod
    async def get_router_id_from_model_name(model_name: str, postgres_session: AsyncSession) -> int | None:
        """
        Retrieve the router ID from a model name, return None if the model name is not found.

        Args:
            model_name(str): The model name

        Returns:
            The router ID
        """
        query = (
            select(RouterTable.id)
            .outerjoin(RouterAliasTable, RouterAliasTable.router_id == RouterTable.id)
            .where(or_(RouterTable.name == model_name, RouterAliasTable.value == model_name))
            .limit(1)
        )
        result = await postgres_session.execute(query)
        router_id = result.scalar_one_or_none()

        return router_id

    async def get_model_provider(
        self,
        model: str,
        endpoint: str,
        postgres_session: AsyncSession,
        redis_client: AsyncRedis,
        request_context: ContextVar[RequestContext],
    ) -> ModelProvider:
        """
        Get a model provider for a given model, endpoint, user priority, postgres_session and redis client.

        Args:
            model(str): The model name
            endpoint(str): The type of endpoint called
            postgres_session(AsyncSession): Database postgres_session
            redis_client(AsyncRedis): Redis client
            request_context(ContextVar[RequestContext]): Request context
        Returns:
            ModelProvider: The chosen provider
        """
        try:
            routers = await self.get_routers(router_id=None, name=model, postgres_session=postgres_session)
        except RouterNotFoundException:
            raise ModelNotFoundException()

        router = routers[0]
        request_context.get().router_id = router.id
        request_context.get().router_name = router.name

        if router.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if (router.cost_prompt_tokens != 0 or router.cost_completion_tokens != 0) and request_context.get().user_info.budget == 0:
            raise InsufficientBudgetException()

        providers = await self.get_providers(router_id=router.id, provider_id=None, postgres_session=postgres_session)

        if len(providers) == 0:
            raise ModelNotFoundException()

        elif self.queuing_enabled:
            # ensure priority is between 0 and max_priority
            priority = max(0, min(int(request_context.get().user_info.priority), self.max_priority))
            provider_id = await apply_routing_with_queuing(
                providers=providers,
                load_balancing_strategy=router.load_balancing_strategy,
                load_balancing_metric=Metric.TTFT,
                retry_countdown=self.retry_countdown,
                max_retries=self.max_retries,
                queue_name=f"{PREFIX__CELERY_QUEUE_ROUTING}.{router.id}",
                priority=priority,
            )

        else:
            provider_id = await apply_routing_without_queuing(
                providers=providers,
                load_balancing_strategy=router.load_balancing_strategy,
                load_balancing_metric=Metric.TTFT,
                retry_countdown=self.retry_countdown,
                max_retries=self.max_retries,
                redis_client=redis_client,
            )

        providers = await self.get_providers(router_id=router.id, provider_id=provider_id, postgres_session=postgres_session)
        provider = providers[0]

        model_provider = ModelProvider.import_module(type=provider.type)(
            url=provider.url,
            key=provider.key,
            timeout=provider.timeout,
            model_name=provider.model_name,
            model_hosting_zone=provider.model_hosting_zone,
            model_total_params=provider.model_total_params,
            model_active_params=provider.model_active_params,
        )
        model_provider.id = provider.id
        model_provider.cost_prompt_tokens = router.cost_prompt_tokens
        model_provider.cost_completion_tokens = router.cost_completion_tokens

        request_context.get().provider_id = provider.id
        request_context.get().provider_model_name = provider.model_name

        return model_provider
