from api.domain.ocr.entities import CreateOCRBody, OCRDocumentURLChunk
from api.tests.unit.use_case.factories import AutenticatedUserFactor
from api.use_cases.ocr import CreateOCRCommand, CreateOCRUseCase


class TestForwardingCommandComposition:
    def _make_command(self) -> CreateOCRCommand:
        return CreateOCRCommand(
            document=OCRDocumentURLChunk(document_url="https://example.com/document.pdf"),
            model="ocr-router",
            authenticated_user=AutenticatedUserFactor(),
        )

    def test_should_add_only_the_authenticated_user_to_the_domain_body_fields(self):
        assert set(CreateOCRCommand.model_fields) == set(CreateOCRBody.model_fields) | {"authenticated_user"}

    def test_should_remain_a_valid_domain_body_when_the_forwarding_command_is_composed_with_it(self):
        command = self._make_command()

        assert isinstance(command, CreateOCRBody)

    def test_should_rebuild_the_body_type_when_the_authenticated_user_is_excluded_from_the_dump(self):
        command = self._make_command()

        payload = command.model_dump(exclude={"authenticated_user"})

        assert "authenticated_user" not in payload
        body = CreateOCRUseCase.BODY_TYPE(**payload)
        assert body.model_dump() == payload
