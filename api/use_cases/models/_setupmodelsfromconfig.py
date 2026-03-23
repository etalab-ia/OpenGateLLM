import logging

from api.domain import SortField, SortOrder
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.schemas.core.configuration import Model as ModelConfiguration
from api.use_cases.admin.providers import CreateProviderUseCase
from api.use_cases.admin.routers import (
    CreateRouterCommand,
    CreateRouterUseCase,
    CreateRouterUseCaseSuccess,
    GetOneRouterUseCaseSuccess,
    GetRoutersCommand,
    GetRoutersUseCase,
    RouterAliasAlreadyExistsError,
    RouterNameAlreadyExistsError,
    RouterNotFoundError,
    UserIsNotAdminError,
)
from 
from api.utils.exceptions import (
    ProviderAlreadyExistsException,
    ProviderNotReachableException,
    UserIsNotAdminError,
)

logger = logging.getLogger(__name__)


class BootstrapModelsCoordinator:
    def __init__(
        self, create_router_use_case: CreateRouterUseCase, get_routers_use_case: GetRoutersUseCase, create_provider_use_case: CreateProviderUseCase
    ) -> None:
        self.create_router_use_case = create_router_use_case
        self.get_routers_use_case = get_routers_use_case
        self.create_provider_use_case = create_provider_use_case

    async def execute(self, models: list[ModelConfiguration]) -> None:
        """
        Set up the model registry by creating the routers and providers from the configuration and
        creating the consumers for the routers. Run in lifespan context.

        Args:
            models(list[ModelConfiguration]): The models to set up
            postgres_session(AsyncSession): The database postgres_session
        """
        for router in models:
            command = CreateRouterCommand(
                name=router.name,
                type=router.type,
                aliases=router.aliases,
                load_balancing_strategy=router.load_balancing_strategy,
                cost_prompt_tokens=router.cost_prompt_tokens,
                cost_completion_tokens=router.cost_completion_tokens,
                user_id=0,  # setup as master user
            )
            result = await self.create_router_use_case.execute(command)

            match result:
                case CreateRouterUseCaseSuccess(created_router):
                    logger.info(f"Router {router.name} successfully created (id: {created_router.id})")
                case RouterAliasAlreadyExistsError(name):
                    logger.info(f"Router {router.name} alias {name} already exists, skipping creation.")
                case RouterNameAlreadyExistsError(name):
                    logger.info(f"Router {router.name} name already exists, skipping creation.")
                case UserIsNotAdminError():
                    logger.info("User is not admin, skipping creation.")

        command = GetRoutersCommand(
            user_id=0,
            offset=0,
            limit=1,
            sort_by=SortField.ID,
            sort_order=SortOrder.ASC,
        )
        result = await self.get_routers_use_case.execute(command)

        match result:
            case GetOneRouterUseCaseSuccess(returned_router):
                routers = 
            case RouterNotFoundError(router_id=not_found_id):
                logger.info(f"Router {model.name} not found, skipping creation.")
            case UserIsNotAdminError():
                logger.info("User is not admin, skipping creation.")

        for router in routers:
            for provider in router.providers:
            try:
                provider_id = await self.create_provider(
                    router_id=router.id,
                    user_id=0,  # setup as master user
                    type=provider.type,
                    url=provider.url,
                    key=provider.key,
                    timeout=provider.timeout,
                    model_name=provider.model_name,
                    model_hosting_zone=provider.model_hosting_zone,
                    model_total_params=provider.model_total_params,
                    model_active_params=provider.model_active_params,
                    qos_metric=provider.qos_metric,
                    qos_limit=provider.qos_limit,
                    postgres_session=postgres_session,
                )
            except ProviderAlreadyExistsException:
                continue
            except ProviderNotReachableException:
                continue
            except Exception as e:
                await postgres_session.rollback()
                logger.error(f"provider {provider.model_name} failed to be created for router {model.name} ({e})")
                raise e
            logging.info(f"provider {provider.model_name} successfully created for router {model.name} (id: {provider_id})")
