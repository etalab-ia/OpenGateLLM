from http import HTTPMethod
import random

import factory
from faker import Faker

from api.domain.provider.entities import ProviderFormattedRequest

fake = Faker()


# Formatted request factories
class VllmFormattedModelRequestFactory(factory.DictFactory):
    class Meta:
        model = ProviderFormattedRequest

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    url = factory.Faker("url")
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        models = factory.Trait(
            method=HTTPMethod.GET,
            endpoint="/v1/models",
        )


# Response factories
class VllmAudioTranscriptionsResponseFactory(factory.DictFactory):
    _status_code = 200

    # body
    text = fake.paragraph()
    usage = {"type": "duration", "seconds": 372}


class VllmChatCompletionsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_id"]

    _status_code = 200

    # parameters
    model_id = factory.Faker("bothify", text="????/???-?#")

    # body
    choices = factory.LazyAttribute(
        lambda self: [
            {
                "finish_reason": "stop",
                "index": 0,
                "logprobs": None,
                "message": {
                    "annotations": None,
                    "audio": None,
                    "content": fake.paragraph(),
                    "function_call": None,
                    "reasoning": fake.paragraph(),
                    "refusal": None,
                    "role": "assistant",
                    "tool_calls": [],
                },
                "stop_reason": None,
                "token_ids": None,
            }
        ]
    )
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    id = factory.Faker("bothify", text="chatcmpl-???###")
    kv_transfer_params = None
    model = factory.LazyAttribute(lambda self: self.model_id)
    object = "chat.completion"
    prompt_logprobs = None
    prompt_token_ids = None
    service_tier = None
    system_fingerprint = None
    usage = {"completion_tokens": 56, "prompt_tokens": 9, "prompt_tokens_details": None, "total_tokens": 65}


class VllmEmbeddingsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["dimensions"]

    _status_code = 200

    # parameters
    dimensions: int = 1024

    # body
    data = factory.LazyAttribute(
        lambda self: [
            {
                "embedding": [fake.pyfloat(min_value=-1, max_value=1, right_digits=6) for _ in range(self.dimensions)],
                "index": 0,
                "object": "embedding",
            }
        ]
    )
    model = factory.Faker("bothify", text="????/???-?#")
    object = "list"
    usage = {"prompt_tokens": 6, "total_tokens": 6}


class VllmMetricsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_name", "running", "waiting"]

    _status_code = 200

    # parameters
    model_name = factory.Faker("bothify", text="????/???-?#")
    running = 0.0
    waiting = 0.0

    # body
    text = factory.LazyAttribute(
        lambda self: (
            f'vllm:num_requests_running{{model_name="{self.model_name}"}} {self.running}\n'
            f'vllm:num_requests_waiting{{model_name="{self.model_name}"}} {self.waiting}\n'
        )
    )


class VllmModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["max_context_length", "model_id", "extra_fields"]

    _status_code = 200

    # parameters
    max_context_length = factory.Faker("random_int", min=1024, max=131072)
    model_id = factory.Faker("bothify", text="????/???-?#")

    object = "list"
    data = factory.LazyAttribute(
        lambda self: [
            {
                "id": self.model_id,
                "object": "model",
                "created": 1773657692,
                "owned_by": "vllm",
                "root": self.model_id,
                "parent": None,
                "max_model_len": self.max_context_length,
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
    )


class VllmRerankResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["count", "top_n", "indices", "relevance_scores", "documents"]

    _status_code = 200

    # parameters
    count = 3
    top_n = None
    documents = factory.LazyAttribute(lambda self: [fake.sentence() for _ in range(self.count)])
    relevance_scores = factory.LazyAttribute(lambda self: [fake.pyfloat(min_value=0, max_value=1, right_digits=9) for _ in range(self.count)])
    indices = factory.LazyAttribute(lambda self: random.sample(range(self.count), self.count))

    # body
    id = factory.Faker("bothify", text="score-?????")
    model = factory.Faker("bothify", text="????/???-?#")
    usage = factory.LazyAttribute(lambda self: {"prompt_tokens": fake.random_int(min=0, max=100), "total_tokens": fake.random_int(min=0, max=100)})
    results = factory.LazyAttribute(
        lambda self: sorted(
            [
                {"index": idx, "document": {"text": doc, "multi_modal": None}, "relevance_score": score}
                for idx, doc, score in zip(self.indices, self.documents, self.relevance_scores)
            ],
            key=lambda x: x["relevance_score"],
            reverse=True,
        )[: self.top_n]
    )


# Error response factories
class VllmNotFoundResponseFactory(factory.DictFactory):
    _status_code = 404

    # body
    detail = "Not found"
