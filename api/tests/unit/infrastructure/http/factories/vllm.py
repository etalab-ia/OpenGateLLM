from http import HTTPMethod

import factory
from faker import Faker

from api.infrastructure.http.model import FormattedModelRequest, OriginalModelResponse

fake = Faker()


# Formatted request factories
class VllmFormattedModelRequestFactory(factory.DictFactory):
    class Meta:
        model = FormattedModelRequest

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    endpoint = factory.Faker("url")
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        models = factory.Trait(
            method=HTTPMethod.GET,
            endpoint="/v1/models",
        )


class VllmOriginalResponseFactory(factory.DictFactory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(lambda: {})
    latency = factory.LazyFunction(lambda: None)

    class Params:
        audio_transcriptions = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "text": fake.paragraph(),
                    "usage": {"type": "duration", "seconds": 372},
                }
            ),
            latency=factory.LazyFunction(lambda: 10),
        )
        chat_completions = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "choices": [
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
                    ],
                    "created": 1774879102,
                    "id": "chatcmpl-9b86775fb2111936",
                    "kv_transfer_params": None,
                    "model": "openai/gpt-oss-120b",
                    "object": "chat.completion",
                    "prompt_logprobs": None,
                    "prompt_token_ids": None,
                    "service_tier": None,
                    "system_fingerprint": None,
                    "usage": {"completion_tokens": 56, "prompt_tokens": 9, "prompt_tokens_details": None, "total_tokens": 65},
                }
            ),
            latency=factory.LazyFunction(lambda: 10),
        )
        embeddings = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "data": [{"embedding": [-0.30128387, 0.5073153, -0.807378], "index": 0, "object": "embedding"}],
                    "model": "BAAI/bge-m3",
                    "object": "list",
                    "usage": {"prompt_tokens": 6, "total_tokens": 6},
                }
            ),
            latency=factory.LazyFunction(lambda: 10),
        )
        models = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "object": "list",
                    "data": [
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
                    ],
                }
            ),
            latency=factory.LazyFunction(lambda: 10),
        )
        rerank = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "results": [
                        {"index": 3, "relevance_score": 0.999071},
                        {"index": 4, "relevance_score": 0.7867867},
                        {"index": 0, "relevance_score": 0.32713068},
                    ],
                    "id": "07734bd2-2473-4f07-94e1-0d9f0e6843cf",
                }
            ),
            latency=factory.LazyFunction(lambda: 10),
        )
