import factory
from faker import Faker

fake = Faker()


# Response factories
class MistralAudioTranscriptionResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_id"]

    _status_code = 200

    # parameters
    model_id = factory.Faker("bothify", text="model-????-####")

    # body
    id = factory.Faker("bothify", text="chatcmpl-???###")
    object = "chat.completion"
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    model = factory.LazyAttribute(lambda self: self.model_id)
    choices = [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": fake.paragraph(),
            },
            "finish_reason": "stop",
        }
    ]
    usage = {
        "prompt_tokens": 42,
        "completion_tokens": 128,
        "total_tokens": 170,
    }


class MistralModelResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_id"]

    _status_code = 200

    # parameters
    model_id = factory.Faker("bothify", text="model-????-####")

    # body
    id = factory.LazyAttribute(lambda self: self.model_id)
    object = "model"
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
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
    name = factory.LazyAttribute(lambda self: self.model_id)
    description = factory.Faker("sentence")
    max_context_length = factory.Faker("random_int", min=64000, max=245600)
    aliases = factory.LazyAttribute(lambda self: [fake.bothify(text="model-????-latest")])
    deprecation = None
    deprecation_replacement_model = None
    default_model_temperature = factory.Faker("pyfloat", min_value=0.1, max_value=1.0)
    type = "base"


class MistralMetricsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_name", "running", "waiting"]

    _status_code = 200

    # parameters
    model_name = factory.Faker("bothify", text="model-????-####")
    running = 0.0
    waiting = 0.0

    # body
    text = factory.LazyAttribute(
        lambda self: (
            f'vllm:num_requests_running{{model_name="{self.model_name}"}} {self.running}\n'
            f'vllm:num_requests_waiting{{model_name="{self.model_name}"}} {self.waiting}\n'
        )
    )


class MistralModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["count"]

    _status_code = 200

    # parameters
    count: int = 1

    # body
    object = "list"
    data = factory.LazyAttribute(lambda self: [MistralModelResponseFactory() for _ in range(self.count)])

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs = super()._adjust_kwargs(**kwargs)

        count = kwargs.get("count", 1)
        data = kwargs.get("data")

        if data is None:
            kwargs["data"] = [MistralModelResponseFactory() for _ in range(count)]
            return kwargs

        normalized_data = list(data)
        if count > len(normalized_data):
            normalized_data.extend(MistralModelResponseFactory() for _ in range(count - len(normalized_data)))

        kwargs["data"] = normalized_data
        return kwargs


class MistralOcrImageFactory(factory.DictFactory):
    class Meta:
        exclude = ["index"]

    # parameters
    index = factory.Faker("random_int", min=0, max=10)

    # body
    bottom_right_x = factory.Faker("random_int", min=0, max=1000)
    bottom_right_y = factory.Faker("random_int", min=0, max=1000)
    id = factory.LazyAttribute(lambda self: f"img-{self.index}.jpeg")
    image_annotation = None
    image_base64 = factory.LazyAttribute(lambda self: f"data:image/jpeg;base64,{fake.binary(length=64)}")
    top_left_x = factory.Faker("random_int", min=0, max=1000)
    top_left_y = factory.Faker("random_int", min=0, max=1000)


class MistralOcrPageFactory(factory.DictFactory):
    class Meta:
        exclude = ["image_count", "hyperlink_count"]

    _status_code = 200

    # parameters
    image_count: int = 0
    hyperlink_count: int = 0

    # body
    dimensions = factory.LazyFunction(
        lambda: {
            "dpi": 200,
            "height": fake.random_int(min=1000, max=2000),
            "width": fake.random_int(min=1000, max=2000),
        }
    )
    footer = None
    header = None
    hyperlinks = factory.LazyAttribute(lambda self: [fake.url() for _ in range(self.hyperlink_count)])
    images = factory.LazyAttribute(lambda self: [MistralOcrImageFactory(index=index) for index in range(self.image_count)])
    index = factory.Faker("random_int", min=0, max=10)
    markdown = fake.paragraph()
    tables = []


class MistralOcrResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["page_count"]

    _status_code = 200

    # parameters
    page_count: int = 2

    # body
    document_annotation = None
    model = factory.Faker("bothify", text="model-????-####")
    pages = factory.LazyAttribute(
        lambda self: [
            MistralOcrPageFactory(
                index=index,
                image_count=fake.random_int(min=0, max=3),
                hyperlink_count=fake.random_int(min=0, max=3),
            )
            for index in range(self.page_count)
        ]
    )
    usage_info = factory.LazyAttribute(
        lambda self: {
            "doc_size_bytes": fake.random_int(min=100000, max=200000),
            "pages_processed": self.page_count,
        }
    )


# Error response factories
class MistralInvalidModelResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["model_id"]

    _status_code = 400

    # parameters
    model_id = factory.Faker("bothify", text="model-????-####")

    # body
    error = {
        "code": "1500",
        "message": factory.LazyAttribute(lambda self: f"Invalid model: {self.model_id}"),
        "object": "error",
        "param": None,
        "type": "invalid_model",
    }
