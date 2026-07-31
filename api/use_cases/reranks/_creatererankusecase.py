from api.domain.model.entities import ModelType as RouterType
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.use_cases._forwarding import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateRerankCommand(ForwardingCommand[CreateRerankBody]): ...


CreateRerankUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateRerankUseCase(ProviderRequestForwardingUseCase[CreateRerankCommand, Rerank]):
    ROUTER_TYPE = RouterType.TEXT_CLASSIFICATION
    ENDPOINT = EndpointRoute.RERANK
