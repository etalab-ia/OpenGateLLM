import random

import factory
from faker import Faker

from api.schemas.chat import CreateChatCompletion
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.utils.variables import EndpointRoute

RERANK_DOCUMENTS_COUNT = 10
RERANK_TOP_N = 2
fake = Faker()


class FormattedRequestContentFactory(factory.DictFactory):
    """Correspond to the request content after passed in the ModelHttpClient._format_request method
    but before the specific formatting in the ModelHttpClient by children classes
    """

    class Meta:
        model = RequestContent

    model = factory.Faker("bothify", text="model-????")
    method = factory.Faker("random_element", elements=["GET", "POST", "PUT", "DELETE"])
    endpoint = factory.Faker("random_element", elements=list(EndpointRoute))
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})
    additional_data = factory.LazyFunction(lambda: {})

    class Params:
        audio_transcriptions = factory.Trait(
            method="POST",
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            form=factory.LazyAttribute(
                lambda self: {
                    "model": self.model,
                    "language": "fr",
                    "prompt": fake.sentence(),
                    "temperature": 0.3,
                    "response_format": "json",
                }
            ),
            files={"file": ("audio.wav", b"test-audio-content", "audio/wav")},
        )
        chat_completions = factory.Trait(
            method="POST",
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            body=factory.LazyAttribute(
                lambda self: CreateChatCompletion(
                    model=self.model,
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
            method="POST",
            endpoint=EndpointRoute.RERANK,
            body=factory.LazyAttribute(
                lambda self: {
                    "model": self.model,
                    "query": fake.sentence(),
                    "documents": fake.sentences(nb=RERANK_DOCUMENTS_COUNT),
                    "top_n": RERANK_TOP_N,
                }
            ),
        )
        embeddings = factory.Trait(method="POST", endpoint=EndpointRoute.EMBEDDINGS, body={"input": ["test", "test2", "test3"]})
        models = factory.Trait(method="GET", endpoint=EndpointRoute.MODELS)


# TEI factories
class TeiFormattedRequestContentFactory(FormattedRequestContentFactory):
    """Correspond to the request content after passed in TEI specific formatting in the TEIModelHttpClient"""

    class Params:
        rerank = factory.Trait(
            method="POST",
            endpoint=EndpointRoute.RERANK,
            body=factory.LazyAttribute(lambda _: {"query": fake.sentence(), "texts": fake.sentences(nb=RERANK_DOCUMENTS_COUNT)}),
            additional_data=factory.LazyAttribute(
                lambda self: {
                    "id": "request-1234567890",
                    "top_n": RERANK_TOP_N,
                    "model": self.model,
                    "usage": Usage(prompt_tokens=10, completion_tokens=10, total_tokens=20).model_dump(),
                }
            ),
        )
        embeddings = factory.Trait(method="POST", endpoint=EndpointRoute.EMBEDDINGS, body={"input": ["test", "test2", "test3"]})
        models = factory.Trait(method="GET", endpoint=EndpointRoute.MODELS)


class TeiRerankItemResponseFactory(factory.DictFactory):
    class Params:
        raw_scores = False
        return_text = False

    index = factory.Faker("random_int", min=0, max=2)
    score = factory.Maybe(
        "raw_scores",
        yes_declaration=factory.Faker("pyfloat", right_digits=6, min_value=0, max_value=1),
        no_declaration=factory.Faker("pyfloat", right_digits=6, min_value=0, max_value=10),
    )
    text = factory.Maybe("return_text", yes_declaration=factory.Faker("sentence"), no_declaration=factory.declarations.SKIP)


class TeiRerankResponseFactory:
    def __new__(cls, request_content: TeiFormattedRequestContentFactory, raw_scores: bool = False, return_text: bool = False):
        len_texts = len(request_content.body["texts"])
        texts_indices = list(range(len_texts))
        random.shuffle(texts_indices)

        return TeiRerankItemResponseFactory.create_batch(
            size=len_texts,
            raw_scores=raw_scores,
            return_text=return_text,
            index=factory.Iterator(texts_indices),
        )


class TeiModelsResponseFactory(factory.DictFactory):
    model_id = "BAAI/bge-m3"
    model_sha = None
    model_dtype = "float16"
    model_type = {"embedding": {"pooling": "cls"}}
    max_concurrent_requests = 512
    max_input_length = 8192
    max_batch_tokens = 16384
    max_batch_requests = None
    max_client_batch_size = 64
    auto_truncate = False
    tokenization_workers = 126
    version = "1.8.3"
    sha = "3120a50a84b22bb3cd84152c11d4373faea6d99a"
    docker_label = "sha-3120a50"

    class Params:
        embedding = factory.Trait(
            model_id="BAAI/bge-m3",
            model_type={"embedding": {"pooling": "cls"}},
        )
        reranker = factory.Trait(
            model_id="BAAI/bge-reranker-v2-m3",
            model_type={"reranker": {"id2label": {"0": "LABEL_0"}, "label2id": {"LABEL_0": 0}}},
        )


# Mistral factories
class MistralModelsItemResponseFactory(factory.DictFactory):
    id = "mistral-medium-2508"
    object = "model"
    created = 1773667856
    owned_by = "mistralai"
    capabilities = {
        "completion_chat": True,
        "function_calling": True,
        "completion_fim": False,
        "fine_tuning": True,
        "vision": True,
        "ocr": False,
        "classification": False,
        "moderation": False,
        "audio": False,
    }
    name = "mistral-medium-2508"
    description = "Update on Mistral Medium 3 with improved capabilities."
    max_context_length = 131072
    aliases = ["mistral-medium-latest"]
    deprecation = None
    deprecation_replacement_model = None
    default_model_temperature = 0.3
    type = "base"

    class Params:
        medium = factory.Trait(
            id="mistral-medium-2508",
            capabilities={
                "completion_chat": True,
                "function_calling": True,
                "completion_fim": False,
                "fine_tuning": True,
                "vision": True,
                "ocr": False,
                "classification": False,
                "moderation": False,
                "audio": False,
            },
            name="mistral-medium-2508",
            description="Update on Mistral Medium 3 with improved capabilities.",
            max_context_length=131072,
            aliases=["mistral-medium-latest"],
            default_model_temperature=0.3,
        )
        embeddings = factory.Trait(
            id="mistral-embed-2312",
            capabilities={
                "completion_chat": False,
                "function_calling": False,
                "completion_fim": False,
                "fine_tuning": False,
                "vision": False,
                "ocr": False,
                "classification": False,
                "moderation": False,
                "audio": False,
            },
            name="mistral-embed-2312",
            description="Our state-of-the-art semantic for extracting representation of text extracts.",
            max_context_length=8192,
            aliases=["mistral-embed-2312", "mistral-embed-latest"],
            default_model_temperature=None,
        )
        ocr = factory.Trait(
            id="mistral-ocr-2512",
            capabilities={
                "completion_chat": False,
                "function_calling": True,
                "completion_fim": False,
                "fine_tuning": False,
                "vision": True,
                "ocr": True,
                "classification": False,
                "moderation": False,
                "audio": False,
            },
            name="mistral-ocr-2512",
            description="Official mistral-ocr-2512 Mistral AI model",
            max_context_length=16384,
            aliases=["mistral-ocr-latest"],
            default_model_temperature=0.0,
        )


class MistralModelsResponseFactory(factory.DictFactory):
    object = "list"
    data = factory.LazyFunction(
        lambda: [
            MistralModelsItemResponseFactory(medium=True),
            MistralModelsItemResponseFactory(embeddings=True),
            MistralModelsItemResponseFactory(ocr=True),
        ]
    )

    class Params:
        text_generation = factory.Trait(
            data=factory.LazyFunction(
                lambda: [
                    MistralModelsItemResponseFactory(medium=True),
                ]
            )
        )
        embeddings = factory.Trait(
            data=factory.LazyFunction(
                lambda: [
                    MistralModelsItemResponseFactory(embeddings=True),
                ]
            )
        )
        ocr = factory.Trait(
            data=factory.LazyFunction(
                lambda: [
                    MistralModelsItemResponseFactory(ocr=True),
                ]
            )
        )


class MistralAudioTranscriptionResponseFactory(factory.DictFactory):
    object = "chat.completion"
    id = factory.Faker("bothify", text="chatcmpl-????????")
    created = factory.Faker("random_int", min=1, max=9999999999)
    model = factory.Faker("bothify", text="mistral-????")
    choices = factory.LazyFunction(
        lambda: [
            {
                "index": 0,
                "message": {"role": "assistant", "tool_calls": None, "content": fake.sentence()},
                "finish_reason": "stop",
            }
        ]
    )
    usage = factory.LazyFunction(lambda: {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20})


# vLLM factories
class VllmModelsResponseFactory(factory.DictFactory):
    object = factory.Faker("random_element", elements=["list"])
    data = [
        {
            "id": "openai/gpt-oss-120b",
            "object": "model",
            "created": 1773657692,
            "owned_by": "vllm",
            "root": "openai/gpt-oss-120b",
            "parent": None,
            "max_model_len": 131072,
            "permission": [
                {
                    "id": "modelperm-aa05efd5693dcdcf",
                    "object": "model_permission",
                    "created": 1773657692,
                    "allow_create_engine": False,
                    "allow_sampling": True,
                    "allow_logprobs": True,
                    "allow_search_indices": False,
                    "allow_view": True,
                    "allow_fine_tuning": False,
                    "organization": "*",
                    "group": None,
                    "is_blocking": False,
                }
            ],
        },
    ]
