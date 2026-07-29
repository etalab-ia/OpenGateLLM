from api.domain.model.entities import ModelType as RouterType
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.use_cases._forwarding import ForwardingCommand, ForwardingUseCase, ForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateRerankCommand(CreateRerankBody, ForwardingCommand): ...


CreateRerankUseCaseSuccess = ForwardingUseCaseSuccess


class CreateRerankUseCase(ForwardingUseCase[CreateRerankCommand, Rerank]):
    ROUTER_TYPE = RouterType.TEXT_CLASSIFICATION
    ENDPOINT = EndpointRoute.RERANK
    BODY_TYPE = CreateRerankBody
