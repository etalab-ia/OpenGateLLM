import asyncio
import logging

from celery.result import AsyncResult
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import Integer, cast, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider as ModelProvider
from api.schemas.admin.providers import Provider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import Router, RouterLoadBalancingStrategy
from api.schemas.core.configuration import Model as ModelConfiguration
from api.schemas.core.metrics import MetricType
from api.schemas.me import UserInfo
from api.schemas.models import Model, ModelCosts, ModelType
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable
from api.tasks.celery_app import celery_app
from api.tasks.queuing import apply_load_balancing_with_queuing
from api.utils.exceptions import (
    InconsistentModelMaxContextLengthException,
    InconsistentModelVectorSizeException,
    InsufficientBudgetException,
    InvalidProviderTypeException,
    MissingProviderURLException,
    ModelIsTooBusyException,
    ModelNotFoundException,
    ProviderAlreadyExistsException,
    ProviderNotFoundException,
    ProviderNotReachableException,
    RouterAliasAlreadyExistsException,
    RouterAlreadyExistsException,
    RouterNotFoundException,
    TaskFailedException,
    WrongModelTypeException,
)
from api.utils.load_balancing import apply_async_load_balancing
from api.utils.qos import apply_async_qos_policy
from api.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    MODEL_TYPE_TO_MODEL_PROVIDER_TYPE_MAPPING = {
        ModelType.AUTOMATIC_SPEECH_RECOGNITION: [
            ProviderType.ALBERT.value,
            ProviderType.OPENAI.value,
            ProviderType.VLLM.value,
        ],
        ModelType.IMAGE_TEXT_TO_TEXT: [
            ProviderType.ALBERT.value,
            ProviderType.OPENAI.value,
            ProviderType.VLLM.value,
        ],
        ModelType.TEXT_EMBEDDINGS_INFERENCE: [
            ProviderType.ALBERT.value,
            ProviderType.OPENAI.value,
            ProviderType.TEI.value,
            ProviderType.VLLM.value,
        ],
        ModelType.TEXT_GENERATION: [
            ProviderType.ALBERT.value,
            ProviderType.OPENAI.value,
            ProviderType.VLLM.value,
        ],
        ModelType.TEXT_CLASSIFICATION: [
            ProviderType.ALBERT.value,
            ProviderType.TEI.value,
        ],
    }
    ENDPOINT_MODEL_TYPE_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: [ModelType.AUTOMATIC_SPEECH_RECOGNITION],
        ENDPOINT__CHAT_COMPLETIONS: [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__EMBEDDINGS: [ModelType.TEXT_EMBEDDINGS_INFERENCE],
        ENDPOINT__OCR: [ModelType.IMAGE_TEXT_TO_TEXT],
        ENDPOINT__RERANK: [ModelType.TEXT_CLASSIFICATION],
    }

    def __init__(
        self,
        app_name: str,
        task_always_eager: bool,
        task_max_priority: int,
        task_soft_time_limit: int,
        task_max_retries: int,
        task_retry_countdown: int,
        queue_name_prefix: str,
    ) -> None:
        self.app_name = app_name
        self.task_always_eager = task_always_eager
        self.task_max_priority = task_max_priority
        self.task_soft_time_limit = task_soft_time_limit
        self.queue_name_prefix = queue_name_prefix
        self.task_max_retries = task_max_retries
        self.task_retry_countdown = task_retry_countdown

        self._aliases: dict[int, list[str]] = {}  # {router_id: [name, alias1, alias2, ...]}
        self._model_providers: dict[int, ModelProvider] = {}

    async def _import_model_configuration(self, models: list[ModelConfiguration], session: AsyncSession) -> None:
        for model in models:
            try:
                router_id = await self.create_router(
                    name=model.name,
                    type=model.type,
                    aliases=model.aliases,
                    load_balancing_strategy=model.load_balancing_strategy,
                    cost_prompt_tokens=model.cost_prompt_tokens,
                    cost_completion_tokens=model.cost_completion_tokens,
                    user_id=None,
                    session=session,
                )
                logger.info(f"Router {model.name} are created (id: {router_id})")
            except RouterAlreadyExistsException:
                logger.warning(f"Router {model.name} already exists, skipping.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating router {model.name}: {e}")
                raise e

            routers = await self.get_routers(router_id=None, name=model.name, session=session)
            router = routers[0]
            self._aliases[router.id] = [router.name]
            if router.aliases is not None:
                self._aliases[router.id] += router.aliases

            for provider in model.providers:
                try:
                    provider_id = await self.create_provider(
                        router_id=router.id,
                        user_id=None,
                        type=provider.type,
                        url=provider.url,
                        key=provider.key,
                        timeout=provider.timeout,
                        model_name=provider.model_name,
                        model_carbon_footprint_zone=provider.model_carbon_footprint_zone,
                        model_carbon_footprint_total_params=provider.model_carbon_footprint_total_params,
                        model_carbon_footprint_active_params=provider.model_carbon_footprint_active_params,
                        qos_metric_type=provider.qos_metric,
                        qos_threshold=provider.qos_threshold,
                        session=session,
                    )
                except ProviderAlreadyExistsException:
                    logger.warning(f"\tProvider {provider.model_name} already exists, skipping.")
                    continue
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error creating provider {provider.model_name} for router {model.name}: {e}")
                    raise
                logging.info(f"\tProvider {provider.model_name} created for router {model.name} with ID {provider_id}")

            providers = await self.get_providers(router_id=router.id, provider_id=None, session=session)
            for provider in providers:
                model_provider = ModelProvider.import_module(provider.type)(
                    url=provider.url,
                    key=provider.key,
                    timeout=provider.timeout,
                    model_name=provider.model_name,
                    model_carbon_footprint_zone=provider.model_carbon_footprint_zone,
                    model_carbon_footprint_total_params=provider.model_carbon_footprint_total_params,
                    model_carbon_footprint_active_params=provider.model_carbon_footprint_active_params,
                    qos_metric=provider.qos_metric,
                    qos_threshold=provider.qos_threshold,
                )
                model_provider.id = provider.id
                self._model_providers[provider.id] = model_provider

    async def create_router(
        self,
        name: str,
        type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
        session: AsyncSession,
    ) -> int:
        """
        Create a new model router without any provider.

        Args:
            name(str): The name of the model (eg. "model-123")
            type(ModelType): The type of model
            aliases(List[str]): List of aliases for the model
            load_balancing_strategy(RouterLoadBalancingStrategy): The routing strategy to use
            cost_prompt_tokens(float): The cost of a million prompt tokens
            cost_completion_tokens(float): The cost of a million completion tokens
            user_id(int): The user ID of owner of the router
            session(AsyncSession): The database session

        Returns:
            The router ID
        """

        # Create the router in database
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
            result = await session.execute(query)
            router_id = result.scalar_one()
        except IntegrityError:
            await session.rollback()
            raise RouterAlreadyExistsException()

        # Check alias integrity
        if aliases:
            query = select(RouterAliasTable.value).where(RouterAliasTable.value.in_(aliases))
            result = await session.execute(query)
            existing_aliases = [alias[0] for alias in result.all()]
            if existing_aliases:
                await session.rollback()
                raise RouterAliasAlreadyExistsException()

        # Add aliases
        if aliases:
            for alias in aliases:
                query = insert(RouterAliasTable).values(value=alias, router_id=router_id)
                await session.execute(query)

        await session.commit()

        self._aliases[router_id] = [name] + aliases

        return router_id

    async def delete_router(self, router_id: int, session: AsyncSession) -> None:
        """
        Delete a model router and all its providers.

        Args:
            router_id(int): The router ID
            session(AsyncSession): Database session
        """
        # Check if router exists
        query = select(RouterTable).where(RouterTable.id == router_id)
        result = await session.execute(query)
        try:
            result.scalar_one()
        except NoResultFound:
            raise RouterNotFoundException()

        # Delete will cascade to providers and aliases due to foreign key constraints
        await session.execute(delete(RouterTable).where(RouterTable.id == router_id))
        await session.commit()

        del self._aliases[router_id]

    async def update_router(
        self,
        router_id: int,
        name: str | None,
        type: ModelType | None,
        aliases: list[str] | None,
        load_balancing_strategy: RouterLoadBalancingStrategy | None,
        cost_prompt_tokens: float | None,
        cost_completion_tokens: float | None,
        user_id: int,
        session: AsyncSession,
    ) -> None:
        """
        Update a model router.

        Args:
            router_id(int): The router ID
            name(Optional[str]): Optional new name
            type(Optional[ModelType]): Optional new type
            aliases(Optional[List[str]]): Optional new aliases list (replaces existing)
            load_balancing_strategy(Optional[RouterLoadBalancingStrategy]): Optional new routing strategy
            cost_prompt_tokens(Optional[float]): Optional new cost of a million prompt tokens
            cost_completion_tokens(Optional[float]): Optional new cost of a million completion tokens
            user_id(int): The user ID of owner of the router
            session(AsyncSession): Database session

        """
        # Check if model exists
        routers = await self.get_routers(router_id=router_id, name=None, session=session)
        router = routers[0]

        # Check alias integrity in aliases of other routers
        if aliases:
            for alias in aliases:
                if router.aliases is not None and alias in router.aliases:
                    raise RouterAliasAlreadyExistsException()

        # Update router properties
        update_values = {}
        if type is not None:
            update_values["type"] = type.value
        if load_balancing_strategy is not None:
            update_values["load_balancing_strategy"] = load_balancing_strategy.value
        if name is not None:
            update_values["name"] = name
        if cost_prompt_tokens is not None:
            update_values["cost_prompt_tokens"] = cost_prompt_tokens
        if cost_completion_tokens is not None:
            update_values["cost_completion_tokens"] = cost_completion_tokens

        if update_values:
            await session.execute(update(RouterTable).where(RouterTable.id == router_id).values(**update_values))

        # Update aliases if provided
        if aliases is not None:
            query = delete(RouterAliasTable).where(RouterAliasTable.router_id == router_id)
            await session.execute(query)
            query = insert(RouterAliasTable).values([{"value": alias, "router_id": router_id} for alias in aliases])
            await session.execute(query)

        await session.commit()

        if name is not None:
            self._aliases[router_id] = [name]
            if router.aliases is not None:
                self._aliases[router.id] += router.aliases
        if aliases is not None:
            self._aliases[router_id] = [router.name] + aliases

    async def get_routers(self, router_id: int | None, name: str | None, session: AsyncSession) -> list[Router]:
        """
        Get model router with optional filtering.

        Args:
            session(AsyncSession): Database session
            router_id(Optional[int]): Optional router ID to filter by
            name(Optional[str]): Optional router name or alias to filter by
        Returns:
            List of model router schemas
        """
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

        if router_id is not None:
            query = query.where(RouterTable.id == router_id)

        result = await session.execute(query)
        router_results = [row._asdict() for row in result.all()]
        if router_id is not None and len(router_results) == 0:
            raise RouterNotFoundException()

        aliases_query = select(RouterAliasTable.router_id.label("router_id"), RouterAliasTable.value)
        if router_id is not None:
            aliases_query = aliases_query.where(RouterAliasTable.router_id == router_id)

        aliases_result = await session.execute(aliases_query)
        aliases = {}
        for row in aliases_result.all():
            if row.router_id not in aliases:
                aliases[row.router_id] = []
            aliases[row.router_id].append(row.value)

        routers = []
        for row in router_results:
            user_id = 0 if row["user_id"] is None else row["user_id"]  # 0 corresponds to master user ID
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

    async def create_provider(
        self,
        router_id: int,
        user_id: int,
        type: ProviderType,
        url: str | None,
        key: str | None,
        timeout: int,
        model_name: str,
        model_carbon_footprint_zone: ProviderCarbonFootprintZone,
        model_carbon_footprint_total_params: float | None,
        model_carbon_footprint_active_params: float | None,
        qos_metric_type: MetricType | None,
        qos_threshold: float | None,
        session: AsyncSession,
    ) -> int:
        """
        Create a new model provider for a router.

        Args:
            router_id(int): The model router ID
            user_id(int): The user ID of owner of the provider
            type(ProviderType): Provider type
            url(Optional[str]): Provider URL
            key(Optional[str]): Provider API key
            timeout(int): Request timeout
            model_name(str): Model name
            model_carbon_footprint_zone(ProviderCarbonFootprintZone | None): ProviderCarbonFootprintZone
            model_carbon_footprint_total_params: float | None
            model_carbon_footprint_active_params: float | None
            qos_metric_type(MetricType | None): QoS metric. If None, no QoS policy is applied.
            qos_threshold(float | None): Optional QoS value
            session(AsyncSession): Database session
        Returns:
            The provider ID
        """
        if url is None:
            if type == ProviderType.OPENAI:
                url = "https://api.openai.com"
            elif type == ProviderType.ALBERT:
                url = "https://albert.api.etalab.gouv.fr"
            else:
                MissingProviderURLException()

        # Check if router exists

        routers = await self.get_routers(router_id=router_id, name=None, session=session)
        router = routers[0]

        if type.value not in self.MODEL_TYPE_TO_MODEL_PROVIDER_TYPE_MAPPING[router.type]:
            raise InvalidProviderTypeException()

        # call model to get the vector size, max context length
        try:
            provider = ModelProvider.import_module(type=type)(
                url=url,
                key=key,
                timeout=timeout,
                model_name=model_name,
                model_carbon_footprint_zone=model_carbon_footprint_zone,
                model_carbon_footprint_total_params=model_carbon_footprint_total_params,
                model_carbon_footprint_active_params=model_carbon_footprint_active_params,
                qos_metric=qos_metric_type,
                qos_threshold=qos_threshold,
            )
        except AssertionError:
            raise ProviderNotReachableException()

        # consistency check
        if router.providers > 0:
            if router.vector_size != provider.vector_size:
                raise InconsistentModelVectorSizeException()
            if router.max_context_length != provider.max_context_length:
                raise InconsistentModelMaxContextLengthException()

        # carbon footprint is only supported for text generation and image text to text models
        if router.type not in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]:
            model_carbon_footprint_active_params = None
            model_carbon_footprint_total_params = None

        # Create provider
        try:
            qos_metric = qos_metric_type.value if qos_metric_type is not None else None
            query = (
                insert(ProviderTable)
                .values(
                    router_id=router_id,
                    user_id=user_id,
                    type=type.value,
                    url=url,
                    key=key,
                    timeout=timeout,
                    model_name=model_name,
                    model_carbon_footprint_zone=model_carbon_footprint_zone,
                    model_carbon_footprint_total_params=model_carbon_footprint_total_params,
                    model_carbon_footprint_active_params=model_carbon_footprint_active_params,
                    qos_metric=qos_metric,
                    qos_threshold=qos_threshold,
                    max_context_length=provider.max_context_length,
                    vector_size=provider.vector_size,
                )
                .returning(ProviderTable.id)
            )
            result = await session.execute(query)
            provider_id = result.scalar_one()
            await session.commit()

        except IntegrityError:
            await session.rollback()
            raise ProviderAlreadyExistsException()

        # store provider in memory
        provider.id = provider_id
        self._model_providers[provider_id] = provider

        return provider_id

    async def delete_provider(
        self,
        router_id: int,
        provider_id: int,
        user_id: int,
        session: AsyncSession,
    ) -> None:
        """
        Delete a model provider by ID.

        Args:
            router_id(int): The router ID
            provider_id(int): The provider ID
            user_id(int): The user ID of owner of the provider
            session(AsyncSession): Database session
        """
        # Check if provider exists
        try:
            query = (
                select(ProviderTable)
                .where(ProviderTable.id == provider_id)
                .where(ProviderTable.user_id == user_id)
                .where(ProviderTable.router_id == router_id)
            )
            result = await session.execute(query)
            result.scalar_one()
        except NoResultFound:
            raise ProviderNotFoundException()

        # Delete provider
        query = delete(ProviderTable).where(ProviderTable.id == provider_id).where(ProviderTable.user_id == user_id)
        await session.execute(query)
        await session.commit()

        del self._model_providers[provider_id]

    async def get_providers(
        self,
        router_id: int,
        provider_id: int | None,
        session: AsyncSession,
    ) -> list[Provider]:
        """
        Get a specific model provider.

        Args:
            router_id(int): The model router ID
            provider_id(Optional[int]): Optional provider ID to filter by
            session: Database session

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
            ProviderTable.model_carbon_footprint_zone,
            ProviderTable.model_carbon_footprint_total_params,
            ProviderTable.model_carbon_footprint_active_params,
            ProviderTable.qos_metric,
            ProviderTable.qos_threshold,
            cast(func.extract("epoch", ProviderTable.created), Integer).label("created"),
            cast(func.extract("epoch", ProviderTable.updated), Integer).label("updated"),
        ).where(ProviderTable.router_id == router_id)

        if provider_id is not None:
            query = query.where(ProviderTable.id == provider_id)

        result = await session.execute(query)
        rows = result.mappings().all()

        if provider_id is not None and len(rows) == 0:
            raise ProviderNotFoundException()

        providers = []
        for row in rows:
            qos_metric = MetricType(row["qos_metric"]) if row["qos_metric"] is not None else None
            user_id = 0 if row["user_id"] is None else row["user_id"]  # 0 corresponds to master user ID
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
                    model_carbon_footprint_zone=row["model_carbon_footprint_zone"],
                    model_carbon_footprint_total_params=row["model_carbon_footprint_total_params"],
                    model_carbon_footprint_active_params=row["model_carbon_footprint_active_params"],
                    qos_metric=qos_metric,
                    qos_threshold=row["qos_threshold"],
                    created=row["created"],
                    updated=row["updated"],
                )
            )

        return providers

    async def get_models(self, name: str | None, user_info: UserInfo, session: AsyncSession) -> list[Model]:
        """
        Get models for a user.

        Args:
            name(Optional[str]): Optional model name to filter by
            user_info(UserInfo): User info of the user to apply the limits to the models
            session(AsyncSession): Database session
        """
        try:
            routers = await self.get_routers(router_id=None, name=name, session=session)
        except RouterNotFoundException:
            raise ModelNotFoundException

        models = []
        for router in routers:
            # skip model if user has no access to it
            has_access = True
            for limit in user_info.limits:
                if limit.router == router.id and limit.value == 0:
                    has_access = False
                    break

            if not has_access:
                if name is not None:
                    raise ModelNotFoundException
                continue

            if router.providers == 0:
                if name is not None:
                    raise ModelNotFoundException
                continue

            # get organization name as owned by
            if user_info.id == 0 or user_info.organization is None:
                owned_by = self.app_name
            else:
                query = (
                    select(UserTable.id, OrganizationTable.name.label("owned_by"))
                    .join(UserTable, UserTable.organization_id == OrganizationTable.id)
                    .where(UserTable.id == router.user_id)
                )
                result = await session.execute(query)
                owned_by = result.all()[0].owned_by
                owned_by = owned_by if owned_by else self.app_name

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

    def _get_router_id_from_model_name(self, model: str) -> int | None:
        """
        Useful method the AccessController and Lifespan to get the router ID from a model name.

        Args:
            model(str): The model name

        Returns:
            The router ID
        """
        searched_router_id = None
        for router_id, aliases in self._aliases.items():
            if model in aliases:
                searched_router_id = router_id
        return searched_router_id

    async def get_model_provider(
        self, model: str, endpoint: str, user_info: UserInfo, session: AsyncSession, redis_client: AsyncRedis
    ) -> ModelProvider:
        """
        Get a model provider for a given model, endpoint, user priority, session and redis client.

        Args:
            model(str): The AI model to use
            endpoint(str): The type of endpoint called
            user_info(UserInfo): The user priority
            session(AsyncSession): Database session
            redis_client(AsyncRedis): Redis client
        Returns:
            ModelProvider: The chosen provider
        """
        try:
            routers = await self.get_routers(router_id=None, name=model, session=session)
        except RouterNotFoundException:
            raise ModelNotFoundException

        router = routers[0]
        if router.type not in self.ENDPOINT_MODEL_TYPE_TABLE[endpoint]:
            raise WrongModelTypeException()

        if (router.cost_prompt_tokens != 0 or router.cost_completion_tokens != 0) and user_info.budget == 0:
            raise InsufficientBudgetException()

        providers = await self.get_providers(router_id=router.id, provider_id=None, session=session)

        # Eager path
        if self.task_always_eager:
            candidates = [provider.id for provider in providers]
            provider_id, performance_indicator = await apply_async_load_balancing(
                candidates=candidates,
                load_balancing_strategy_name=router.load_balancing_strategy,
                load_balancing_metric=MetricType.TTFT,
                redis_client=redis_client,
            )
            provider = self._model_providers[provider_id]
            can_be_forwarded = await apply_async_qos_policy(
                provider_id=provider_id,
                qos_metric=provider.qos_metric,
                qos_threshold=provider.qos_threshold,
                performance_indicator=performance_indicator,
                redis_client=redis_client,
            )
            if not can_be_forwarded:
                raise ModelIsTooBusyException()

            provider.cost_prompt_tokens = router.cost_prompt_tokens
            provider.cost_completion_tokens = router.cost_completion_tokens

            return provider

        # Celery path
        candidates = []
        for provider in providers:
            qos_metric = provider.qos_metric.value if provider.qos_metric is not None else None
            candidates.append((provider.id, qos_metric, provider.qos_threshold))

        priority = max(0, min(int(user_info.priority), self.task_max_priority - 1))  # 0-(n-1) usable priorities (n levels)
        task = apply_load_balancing_with_queuing.apply_async(
            args=[
                candidates,  # candidates
                router.load_balancing_strategy,  # load_balancing_strategy
                MetricType.TTFT,  # load_balancing_metric
                self.task_retry_countdown,  # task_retry_countdown
                self.task_max_retries,  # task_max_retries
            ],
            queue=f"{self.queue_name_prefix}.{router.id}",
            priority=priority,
        )

        async_result = AsyncResult(id=task.id, app=celery_app)
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        # wait until the task is ready or timeout is reached
        while not async_result.ready():
            if loop.time() - start_time > self.task_soft_time_limit:
                raise TimeoutError(f"Task {task.id} timed out after {self.task_soft_time_limit} seconds")
            await asyncio.sleep(0.1)  # TODO: variabiliser

        try:
            result = async_result.result  # direct access is safe after ready() returns True
            if result["status_code"] != 200:
                raise TaskFailedException(status_code=result["status_code"], detail=result["body"]["detail"])
            provider = self._model_providers[result["provider_id"]]
            provider.cost_prompt_tokens = router.cost_prompt_tokens
            provider.cost_completion_tokens = router.cost_completion_tokens

            return provider

        except Exception as e:
            logger.warning(f"Error retrieving result for task {task.id}: {e}")
            raise TaskFailedException(detail=str(e))
