from api.domain.model.entities import ModelType as RouterType
from api.domain.ocr.entities import OCR, CreateOCRBody
from api.domain.router.entities import Router
from api.use_cases._forwarding import ForwardingCommand, ForwardingUseCase, ForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateOCRCommand(ForwardingCommand[CreateOCRBody]): ...


CreateOCRUseCaseSuccess = ForwardingUseCaseSuccess


class CreateOCRUseCase(ForwardingUseCase[CreateOCRCommand, OCR]):
    ROUTER_TYPE = RouterType.IMAGE_TO_TEXT
    ENDPOINT = EndpointRoute.OCR

    def _completion_tokens(self, data: OCR) -> int:
        return self.model_tokenizer.compute_tokens(texts=data.get_output_texts())

    def _is_billable(self, router: Router) -> bool:
        return router.is_billable
