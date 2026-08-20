from api.domain.model.entities import ModelType as RouterType
from api.domain.ocr.entities import OCR, CreateOCRBody
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseSuccess,
)
from api.utils.variables import EndpointRoute


class CreateOCRCommand(ForwardingCommand[CreateOCRBody]): ...


CreateOCRUseCaseSuccess = ProviderRequestForwardingUseCaseSuccess


class CreateOCRUseCase(ProviderRequestForwardingUseCase[CreateOCRCommand, OCR]):
    ROUTER_TYPE = RouterType.IMAGE_TO_TEXT
    ENDPOINT = EndpointRoute.OCR
