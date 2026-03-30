import factory

from api.infrastructure.http.model import OriginalModelResponse


class OpenaiOriginalResponseFactory(factory.DictFactory):
    class Meta:
        model = OriginalModelResponse

    data = factory.LazyFunction(lambda: {})
    latency = factory.LazyFunction(lambda: None)

    class Params:
        models = factory.Trait(
            data=factory.LazyFunction(
                lambda: {
                    "object": "list",
                    "data": [
                        {"created": 1686588896, "id": "gpt-4-0613", "object": "model", "owned_by": "openai"},
                        {"created": 1687882411, "id": "gpt-4", "object": "model", "owned_by": "openai"},
                        {"created": 1677610602, "id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
                        {"created": 1773451123, "id": "gpt-5.4-mini", "object": "model", "owned_by": "system"},
                        {"created": 1772691852, "id": "gpt-5.4", "object": "model", "owned_by": "system"},
                    ],
                }
            ),
        )
        latency = None
