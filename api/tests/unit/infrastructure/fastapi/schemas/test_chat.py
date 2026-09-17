from api.domain.chat.entities import CreateChatCompletionsBody as DomainChatCompletionsBody
from api.infrastructure.fastapi.schemas.chat import CreateChatCompletionsBody as ApiChatCompletionsBody

# every shared field must declare the same type on both sides; a divergence here is a 500 waiting to happen
KNOWN_DIVERGENCES = {}


class TestCreateChatCompletionsBodyMatchesDomainPayload:
    """The endpoint builds the domain payload from `body.model_dump()` inside its `try`, so a type the API schema accepts and the
    domain payload rejects raises a ValidationError that the generic handler turns into a 500 instead of a 422."""

    def test_should_declare_the_same_fields_as_the_domain_payload(self):
        assert set(ApiChatCompletionsBody.model_fields) == set(DomainChatCompletionsBody.model_fields)

    def test_should_declare_the_same_annotations_as_the_domain_payload(self):
        shared_fields = set(ApiChatCompletionsBody.model_fields) & set(DomainChatCompletionsBody.model_fields)

        divergences = {
            name: (ApiChatCompletionsBody.model_fields[name].annotation, DomainChatCompletionsBody.model_fields[name].annotation)
            for name in shared_fields
            if ApiChatCompletionsBody.model_fields[name].annotation != DomainChatCompletionsBody.model_fields[name].annotation
        }

        assert divergences == KNOWN_DIVERGENCES
