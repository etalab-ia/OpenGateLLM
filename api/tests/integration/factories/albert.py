import factory
from faker import Faker

from api.domain.model.entities import ModelCosts, ModelType

fake = Faker()


# Response factories
class AlbertModelResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model"]

    _status_code = 200

    # parameters
    model = factory.Faker("bothify", text="????/???-?#")

    # body
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    id = factory.LazyAttribute(lambda self: self.model)
    aliases = factory.LazyFunction(lambda: [fake.bothify(text="????/???-?#")])
    object = "model"
    owned_by = "albert"
    type = factory.Faker("random_element", elements=list(ModelType))
    max_context_length = factory.Faker("random_int", min=1024, max=8192)
    costs = factory.LazyFunction(
        lambda: ModelCosts(
            prompt_tokens=fake.pyfloat(min_value=0, max_value=1, right_digits=4),
            completion_tokens=fake.pyfloat(min_value=0, max_value=1, right_digits=4),
        ).model_dump()
    )


class AlbertModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["count", "max_context_length", "model"]

    _status_code = 200

    # parameters
    count: int = 1
    model = factory.Faker("bothify", text="????/???-?#")
    max_context_length = factory.Faker("random_int", min=1024, max=8192)

    # body
    object = "list"
    data = factory.LazyAttribute(
        lambda self: [AlbertModelResponseFactory(model=self.model, max_context_length=self.max_context_length) for _ in range(self.count)]
    )

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs = super()._adjust_kwargs(**kwargs)

        count = kwargs.get("count", 1)
        data = kwargs.get("data")

        if data is None:
            kwargs["data"] = [AlbertModelResponseFactory() for _ in range(count)]
            return kwargs

        normalized_data = list(data)
        if count > len(normalized_data):
            normalized_data.extend(AlbertModelResponseFactory() for _ in range(count - len(normalized_data)))

        kwargs["data"] = normalized_data
        return kwargs


# Error response factories
class AlbertWrongModelTypeResponseFactory(factory.DictFactory):
    _status_code = 422

    # body
    detail = "Wrong model type."
