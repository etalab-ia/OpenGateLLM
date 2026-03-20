import factory
from faker import Faker

from api.domain.model.entities import UserModelRequest
from api.infrastructure.http.model import ModelHttpExchange, OriginalModelRequest
from api.schemas.chat import CreateChatCompletion
from api.utils.variables import EndpointRoute

RERANK_DOCUMENTS_COUNT = 3
RERANK_TOP_N = 2
fake = Faker()


class UserModelRequestFactory(factory.DictFactory):
    """Correspond to the request content after passed in the ModelHttpClient._format_request method
    but before the specific formatting in the ModelHttpClient by children classes
    """

    class Meta:
        model = UserModelRequest

    endpoint = factory.Faker("random_element", elements=list(EndpointRoute))
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        audio_transcriptions = factory.Trait(
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            form=factory.LazyAttribute(
                lambda self: {
                    "model": "openweight-audio",
                    "language": "fr",
                    "prompt": fake.sentence(),
                    "temperature": 0.3,
                    "response_format": "json",
                }
            ),
            files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
        )
        chat_completions = factory.Trait(
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            body=factory.LazyAttribute(
                lambda self: CreateChatCompletion(
                    model="openweight-large",
                    messages=[
                        {"role": "system", "content": fake.sentence()},
                        {"role": "user", "content": fake.sentence()},
                        {"role": "assistant", "content": fake.sentence()},
                        {"role": "user", "content": fake.sentence()},
                    ],
                    frequency_penalty=None,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "DummyResponseFormat",
                            "schema": {
                                "properties": {
                                    "dummy_list": {"items": {"type": "string"}, "title": "Dummy List", "type": "array"},
                                    "dummy_str": {"title": "Dummy Str", "type": "string"},
                                    "dummy_optional_bool": {"default": False, "title": "Dummy Optional Bool", "type": "boolean"},
                                    "dummy_nullable_int": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Dummy Nullable Int"},
                                },
                                "required": ["dummy_list", "dummy_str", "dummy_nullable_int"],
                                "title": "DummyResponseFormat",
                                "type": "object",
                            },
                        },
                    },
                    tool_choice="required",
                    seed=10,
                    stop=None,
                    stream=False,
                ).model_dump()
            ),
        )
        rerank = factory.Trait(
            endpoint=EndpointRoute.RERANK,
            body=factory.LazyAttribute(
                lambda self: {
                    "model": "openweight-rerank",
                    "query": fake.sentence(),
                    "documents": fake.sentences(nb=RERANK_DOCUMENTS_COUNT),
                    "top_n": RERANK_TOP_N,
                }
            ),
        )
        embeddings = factory.Trait(
            endpoint=EndpointRoute.EMBEDDINGS,
            body=factory.LazyAttribute(
                lambda self: {
                    "model": "openweight-embed",
                    "input": fake.sentences(nb=RERANK_DOCUMENTS_COUNT),
                }
            ),
        )
        models = factory.Trait(endpoint=EndpointRoute.MODELS)


class OriginalModelRequestFactory(UserModelRequestFactory):
    class Meta:
        model = OriginalModelRequest


class HttpModelExchangeFactory(factory.Factory):
    class Meta:
        model = ModelHttpExchange

    original_request = factory.SubFactory(OriginalModelRequestFactory)
    formatted_request = None
    original_response = None
    formatted_response = None

    class Params:
        audio_transcriptions = factory.Trait(original_request=factory.SubFactory(OriginalModelRequestFactory, audio_transcriptions=True))
        chat_completions = factory.Trait(original_request=factory.SubFactory(OriginalModelRequestFactory, chat_completions=True))
        embeddings = factory.Trait(original_request=factory.SubFactory(OriginalModelRequestFactory, embeddings=True))
        models = factory.Trait(original_request=factory.SubFactory(OriginalModelRequestFactory, models=True))
        rerank = factory.Trait(original_request=factory.SubFactory(OriginalModelRequestFactory, rerank=True))
