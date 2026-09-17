from api.domain.ocr.entities import OCR, CreateOCRBody
from api.domain.router.entities import RouterType
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseResult,
    ProviderRequestForwardingUseCaseSuccess,
)
from api.utils.variables import EndpointRoute


class CreateOCRCommand(ForwardingCommand[CreateOCRBody]): ...


CreateOCRUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateOCRUseCase(ProviderRequestForwardingUseCase[CreateOCRCommand, ProviderRequestForwardingUseCaseResult[OCR]]):
    ROUTER_TYPE = RouterType.IMAGE_TO_TEXT
    ENDPOINT = EndpointRoute.OCR
