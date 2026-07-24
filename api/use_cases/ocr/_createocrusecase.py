from api.domain.model.entities import ModelType as RouterType
from api.domain.ocr.entities import OCR, CreateOCRBody
from api.use_cases._forwarding import PromptOnlyForwardingUseCase, PromptOnlyForwardingUseCaseSuccess, RequestContextCarrier
from api.utils.variables import EndpointRoute


class CreateOCRCommand(CreateOCRBody, RequestContextCarrier): ...


CreateOCRUseCaseSuccess = PromptOnlyForwardingUseCaseSuccess


class CreateOCRUseCase(PromptOnlyForwardingUseCase[CreateOCRCommand, OCR]):
    ROUTER_TYPE = RouterType.IMAGE_TO_TEXT
    ENDPOINT = EndpointRoute.OCR
    BODY_TYPE = CreateOCRBody
