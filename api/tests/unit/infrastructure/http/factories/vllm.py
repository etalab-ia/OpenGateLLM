from http import HTTPMethod

import factory

from api.infrastructure.http.model import FormattedModelRequest, OriginalModelResponse


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


# Original response factories
class VllmModelsOriginalResponseFactory(factory.Factory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(
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
    )


class VllmOriginalResponseFactory:
    def __new__(cls, models=False, **kwargs):
        if models:
            return VllmModelsOriginalResponseFactory(**kwargs)
        return OriginalModelResponse()
