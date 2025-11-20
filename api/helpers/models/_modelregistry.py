from contextvars import ContextVar
import logging

from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import Integer, cast, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider as ModelProvider
from api.schemas.admin.providers import Provider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import Router, RouterLoadBalancingStrategy
from api.schemas.core.configuration import Model as ModelConfiguration
from api.schemas.core.context import RequestContext
from api.schemas.core.metrics import Metric
from api.schemas.me.info import UserInfo
from api.schemas.models import Model, ModelCosts, ModelType
from api.sql.models import Organization as OrganizationTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import RouterAlias as RouterAliasTable
from api.sql.models import User as UserTable
from api.tasks import add_model_queue_to_running_worker
from api.utils.exceptions import (
    InconsistentModelMaxContextLengthException,
    InconsistentModelVectorSizeException,
    InsufficientBudgetException,
    InvalidProviderTypeException,
    MissingProviderURLException,
    ModelNotFoundException,
    ProviderAlreadyExistsException,
    ProviderNotFoundException,
    ProviderNotReachableException,
    RouterAliasAlreadyExistsException,
    RouterAlreadyExistsException,
    RouterNotFoundException,
    WrongModelTypeException,
)
from api.utils.routing import apply_routing_with_queuing, apply_routing_without_queuing
from api.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
    PREFIX__CELERY_QUEUE_ROUTING,
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
            ProviderType.MISTRAL.value,
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
            ProviderType.MISTRAL.value,
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

    async def setup(self, models: list[ModelConfiguration], postgres_session: AsyncSession) -> None:
        """
        Setup the model registry by creating the routers and providers from the configuration and
        creating the consumers for the routers. Run in lifespan context.

        Args:
            models(list[ModelConfiguration]): The models to setup
            postgres_session(AsyncSession): The database postgres_session
        """
        for model in models:
            try:
                router_id = await self.create_router(
                    name=model.name,
                    type=model.type,
                    aliases=model.aliases,
                    load_balancing_strategy=model.load_balancing_strategy,
                    cost_prompt_tokens=model.cost_prompt_tokens,
                    cost_completion_tokens=model.cost_completion_tokens,
                    user_id=0,  # setup as master user
                    postgres_session=postgres_session,
                )
                logger.info(f"Router {model.name} are created (id: {router_id})")
            except RouterAlreadyExistsException:
                logger.warning(f"Router {model.name} already exists, skipping.")
            except RouterAliasAlreadyExistsException:
                logger.warning(f"Router {model.name} aliases already exists, skipping.")
                continue
            except Exception as e:
                await postgres_session.rollback()
                logger.error(f"Error creating router {model.name}: {e}")
                raise e

            routers = await self.get_routers(router_id=None, name=model.name, postgres_session=postgres_session)
            router = routers[0]

            for provider in model.providers:
                try:
                    provider_id = await self.create_provider(
                        router_id=router.id,
                        user_id=0,  # setup as master user
                        type=provider.type,
                        url=provider.url,
                        key=provider.key,
                        timeout=provider.timeout,
                        model_name=provider.model_name,
                        model_carbon_footprint_zone=provider.model_carbon_footprint_zone,
                        model_carbon_footprint_total_params=provider.model_carbon_footprint_total_params,
                        model_carbon_footprint_active_params=provider.model_carbon_footprint_active_params,
                        qos_metric=provider.qos_metric,
                        qos_limit=provider.qos_limit,
                        postgres_session=postgres_session,
                    )
                except ProviderAlreadyExistsException:
                    logger.warning(f"Provider {provider.model_name} already exists for router {model.name} (skipping)")
                    continue
                except Exception as e:
                    await postgres_session.rollback()
                    logger.error(f"Provider {provider.model_name} failed to be created for router {model.name} ({e})")
                    raise e
                logging.info(f"Provider {provider.model_name} successfully created for router {model.name} (id: {provider_id})")

            if self.queuing_enabled:
                routers = await self.get_routers(router_id=None, name=None, postgres_session=postgres_session)
                for router in routers:
                    add_model_queue_to_running_worker(queue_name=f"{PREFIX__CELERY_QUEUE_ROUTING}.{router.id}")

    async def create_router(
        self,
        name: str,
        type: ModelType,
        aliases: list[str],
        load_balancing_strategy: RouterLoadBalancingStrategy,
        cost_prompt_tokens: float,
        cost_completion_tokens: float,
        user_id: int,
        postgres_session: AsyncSession,
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
            postgres_session(AsyncSession): The database postgres_session

        Returns:
            The router ID
        """

        # Create the router in database
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
            result = await postgres_session.execute(query)
            router_id = result.scalar_one()
        except IntegrityError:
            await postgres_session.rollback()
            raise RouterAlreadyExistsException()

        # Check alias integrity
        if aliases:
            query = select(RouterAliasTable.value).where(RouterAliasTable.value.in_(aliases))
            result = await postgres_session.execute(query)
            existing_aliases = [alias[0] for alias in result.all()]
            if existing_aliases:
                await postgres_session.rollback()
                raise RouterAliasAlreadyExistsException()

        # Add aliases
        if aliases:
            for alias in aliases:
                query = insert(RouterAliasTable).values(value=alias, router_id=router_id)
                await postgres_session.execute(query)

        await postgres_session.commit()

        if self.queuing_enabled:
            add_model_queue_to_running_worker(queue_name=f"{PREFIX__CELERY_QUEUE_ROUTING}.{router_id}")

        return router_id

    async def delete_router(self, router_id: int, postgres_session: AsyncSession) -> None:
        """
        Delete a model router and all its providers.

        Args:
            router_id(int): The router ID
            postgres_session(AsyncSession): Database postgres_session
        """
        # Check if router exists
        query = select(RouterTable).where(RouterTable.id == router_id)
        result = await postgres_session.execute(query)
        try:
            result.scalar_one()
        except NoResultFound:
            raise RouterNotFoundException()

        # Delete will cascade to providers and aliases due to foreign key constraints
        await postgres_session.execute(delete(RouterTable).where(RouterTable.id == router_id))
        await postgres_session.commit()

        # TODO: delete queue

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
        postgres_session: AsyncSession,
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
            postgres_session(AsyncSession): Database postgres_session

        """
        # Check if model exists
        routers = await self.get_routers(router_id=router_id, name=None, postgres_session=postgres_session)
        router = routers[0]

        # Check alias integrity in aliases of other routers
        if aliases:
            query = select(RouterAliasTable.router_id).where(RouterAliasTable.value.in_(aliases)).where(RouterAliasTable.router_id != router_id)
            result = await postgres_session.execute(query)
            conflicting_aliases = result.scalars().all()
            if conflicting_aliases:
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
            await postgres_session.execute(update(RouterTable).where(RouterTable.id == router_id).values(**update_values))

        # Update aliases if provided
        if aliases is not None:
            query = delete(RouterAliasTable).where(RouterAliasTable.router_id == router_id)
            await postgres_session.execute(query)
            query = insert(RouterAliasTable).values([{"value": alias, "router_id": router_id} for alias in aliases])
            await postgres_session.execute(query)

        await postgres_session.commit()

    async def get_routers(self, router_id: int | None, name: str | None, postgres_session: AsyncSession) -> list[Router]:
        """
        Get model router with optional filtering.

        Args:
            postgres_session(AsyncSession): Database postgres_session
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
        model_carbon_footprint_total_params: int | None,
        model_carbon_footprint_active_params: int | None,
        qos_metric: Metric | None,
        qos_limit: float | None,
        postgres_session: AsyncSession,
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
            model_carbon_footprint_total_params: int | None
            model_carbon_footprint_active_params: int | None
            qos_metric(Metric | None): QoS metric. If None, no QoS policy is applied.
            qos_limit(float | None): Optional QoS limit
            postgres_session(AsyncSession): Database postgres_session
        Returns:
            The provider ID
        """
        if url is None:
            if type == ProviderType.OPENAI:
                url = "https://api.openai.com"
            elif type == ProviderType.ALBERT:
                url = "https://albert.api.etalab.gouv.fr"
            else:
                raise MissingProviderURLException()

        # check if router exists
        routers = await self.get_routers(router_id=router_id, name=None, postgres_session=postgres_session)
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
            )
            max_context_length = await provider.get_max_context_length()
            if router.type == ModelType.TEXT_EMBEDDINGS_INFERENCE:
                vector_size = await provider.get_vector_size()
            else:
                vector_size = None

        except AssertionError as e:
            logger.debug(f"Provider {provider.name} not reachable: {e}", exc_info=True)
            raise ProviderNotReachableException()

        # consistency check
        if router.providers > 0:
            if router.vector_size != vector_size:
                raise InconsistentModelVectorSizeException()
            if router.max_context_length != max_context_length:
                raise InconsistentModelMaxContextLengthException()

        # carbon footprint is only supported for text generation and image text to text models
        if router.type not in [ModelType.TEXT_GENERATION, ModelType.IMAGE_TEXT_TO_TEXT]:
            model_carbon_footprint_active_params = None
            model_carbon_footprint_total_params = None

        # Create provider
        try:
            user_id = None if user_id == 0 else user_id  # 0 corresponds to master user ID
            qos_metric = qos_metric.value if qos_metric is not None else None
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
                    qos_limit=qos_limit,
                    max_context_length=max_context_length,
                    vector_size=vector_size,
                )
                .returning(ProviderTable.id)
            )
            result = await postgres_session.execute(query)
            provider_id = result.scalar_one()
            await postgres_session.commit()

        except IntegrityError:
            await postgres_session.rollback()
            raise ProviderAlreadyExistsException()

        return provider_id

    async def delete_provider(
        self,
        provider_id: int,
        user_id: int,
        postgres_session: AsyncSession,
    ) -> None:
        """
        Delete a model provider by ID.

        Args:
            router_id(int): The router ID
            provider_id(int): The provider ID
            user_id(int): The user ID of owner of the provider
            postgres_session(AsyncSession): Database postgres_session
        """
        # Check if provider exists
        try:
            query = select(ProviderTable).where(ProviderTable.id == provider_id).where(ProviderTable.user_id == user_id)
            result = await postgres_session.execute(query)
            result.scalar_one()
        except NoResultFound:
            raise ProviderNotFoundException()

        # Delete provider
        query = delete(ProviderTable).where(ProviderTable.id == provider_id).where(ProviderTable.user_id == user_id)
        await postgres_session.execute(query)
        await postgres_session.commit()

    async def get_providers(
        self,
        router_id: int,
        provider_id: int | None,
        postgres_session: AsyncSession,
    ) -> list[Provider]:
        """
        Get a specific model provider.

        Args:
            router_id(int): The model router ID
            provider_id(Optional[int]): Optional provider ID to filter by
            postgres_session: Database postgres_session

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
            ProviderTable.qos_limit,
            cast(func.extract("epoch", ProviderTable.created), Integer).label("created"),
            cast(func.extract("epoch", ProviderTable.updated), Integer).label("updated"),
        )

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
            # skip model if user has no access to it
            has_access = True
            for limit in user_info.limits:
                if limit.router == router.id and limit.value == 0:
                    has_access = False
                    break

            if not has_access:
                if name is not None:
                    raise ModelNotFoundException()
                continue

            if router.providers == 0:
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

    async def get_router_id_from_model_name(self, model_name: str, postgres_session: AsyncSession) -> int | None:
        """
        Retrieve the router ID from a model name, return None if the model name is not found.

        Args:
            model_name(str): The model name

        Returns:
            The router ID
        """
        query = (
            select(RouterTable.id)
            .where(or_(RouterTable.name == model_name, RouterAliasTable.value == model_name))
            .join(RouterAliasTable, RouterAliasTable.router_id == RouterTable.id)
        ).limit(1)

        result = await postgres_session.execute(query)
        router_id = result.scalar_one_or_none()

        if router_id is not None:
            return router_id

        return None

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
            model_carbon_footprint_zone=provider.model_carbon_footprint_zone,
            model_carbon_footprint_total_params=provider.model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=provider.model_carbon_footprint_active_params,
        )
        model_provider.id = provider.id
        model_provider.cost_prompt_tokens = router.cost_prompt_tokens
        model_provider.cost_completion_tokens = router.cost_completion_tokens

        request_context.get().provider_id = provider.id
        request_context.get().provider_model_name = provider.model_name

        return model_provider
