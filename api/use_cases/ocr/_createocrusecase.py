from api.domain.model.entities import ModelType as RouterType
from api.domain.ocr.entities import OCR, CreateOCRBody
from api.domain.router.entities import Router
from api.use_cases._forwarding import ForwardingCommand, ForwardingUseCase, ForwardingUseCaseSuccess
from api.utils.variables import EndpointRoute


class CreateOCRCommand(CreateOCRBody, ForwardingCommand): ...


CreateOCRUseCaseSuccess = ForwardingUseCaseSuccess


class CreateOCRUseCase(ForwardingUseCase[CreateOCRCommand, OCR]):
    ROUTER_TYPE = RouterType.IMAGE_TO_TEXT
    ENDPOINT = EndpointRoute.OCR
    BODY_TYPE = CreateOCRBody

    @staticmethod
    def _extract_output_texts(ocr: OCR) -> list[str]:
        texts = [page.markdown for page in ocr.pages if page.markdown]
        if ocr.document_annotation:
            texts.append(ocr.document_annotation)
        return texts

    def _completion_tokens(self, data: OCR) -> int:
        return self.model_tokenizer.compute_tokens(texts=self._extract_output_texts(data))

    def _is_billable(self, router: Router) -> bool:
        return router.is_billable
