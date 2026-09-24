from api.domain.provider.entities import ProviderEndpoint
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.domain.router.entities import RouterType
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseResult,
    ProviderRequestForwardingUseCaseSuccess,
)


class CreateRerankCommand(ForwardingCommand[CreateRerankBody]): ...


CreateRerankUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateRerankUseCase(ProviderRequestForwardingUseCase[CreateRerankCommand, ProviderRequestForwardingUseCaseResult[Rerank]]):
    ROUTER_TYPE = RouterType.TEXT_CLASSIFICATION
    ENDPOINT = ProviderEndpoint.RERANK
