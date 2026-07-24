from contextvars import ContextVar

from api.domain.ocr.entities import CreateOCRBody, OCRDocumentURLChunk
from api.infrastructure.fastapi.context import RequestContext
from api.tests.unit.use_case.factories import AutenticatedUserFactor
from api.use_cases.ocr import CreateOCRCommand


class TestRequestContextCarrierComposition:
    """CreateXCommand composes a domain body with the RequestContextCarrier mixin (pydantic multiple inheritance)."""

    def _make_command(self) -> CreateOCRCommand:
        request_context = ContextVar("request_context")
        request_context.set(RequestContext(user=AutenticatedUserFactor()))
        return CreateOCRCommand(
            document=OCRDocumentURLChunk(document_url="https://example.com/document.pdf"),
            model="ocr-router",
            request_context=request_context,
        )

    def test_accepts_context_var_field(self):
        # arbitrary_types_allowed from the mixin must be inherited so the ContextVar field validates
        command = self._make_command()

        assert isinstance(command.request_context, ContextVar)

    def test_preserves_body_fields(self):
        command = self._make_command()

        assert command.model == "ocr-router"
        assert isinstance(command, CreateOCRBody)

    def test_model_dump_excluding_request_context_rebuilds_the_domain_body(self):
        command = self._make_command()

        payload = command.model_dump(exclude={"request_context"})

        assert "request_context" not in payload
        # BODY_TYPE(**payload) is exactly what the base use case forwards to the provider
        body = CreateOCRBody(**payload)
        assert body.model_dump() == payload

    def test_set_value_in_request_context_mutates_the_context(self):
        command = self._make_command()

        command.set_value_in_request_context(key="router_id", value=42)

        assert command.request_context.get().router_id == 42
