import factory
from faker import Faker

fake = Faker()


# Response factories
class OpenaiModelResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model"]

    _status_code = 200

    # parameters
    model = factory.Faker("bothify", text="model-????-####")

    # body
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    id = factory.LazyAttribute(lambda self: self.model)
    object = "model"
    owned_by = "openai"


class OpenaiModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["count", "max_context_length"]

    _status_code = 200

    # parameters
    count: int = 1
    model = factory.Faker("bothify", text="model-????-####")

    # body
    object = "list"
    data = factory.LazyAttribute(lambda self: [OpenaiModelResponseFactory(model=self.model) for _ in range(self.count)])

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs = super()._adjust_kwargs(**kwargs)

        count = kwargs.get("count", 1)
        data = kwargs.get("data")

        if data is None:
            kwargs["data"] = [OpenaiModelResponseFactory() for _ in range(count)]
            return kwargs

        normalized_data = list(data)
        if count > len(normalized_data):
            normalized_data.extend(OpenaiModelResponseFactory() for _ in range(count - len(normalized_data)))

        kwargs["data"] = normalized_data
        return kwargs


# Error response factories
class OpenaiNotEmbeddingModelResponseFactory(factory.DictFactory):
    _status_code = 403

    # body
    error = {
        "code": None,
        "message": "You are not allowed to generate embeddings from this model",
        "param": None,
        "type": "invalid_request_error",
    }
