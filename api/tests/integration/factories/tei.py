from http import HTTPMethod
import random

import factory
from faker import Faker

from api.infrastructure.http.model.exchanges import FormattedModelRequest

fake = Faker()


# Formatted request factories
class TeiFormattedModelRequestFactory(factory.DictFactory):
    class Meta:
        model = FormattedModelRequest

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    url = factory.Faker("url")
    body = factory.LazyFunction(lambda: {})
    form = factory.LazyFunction(lambda: {})
    files = factory.LazyFunction(lambda: {})

    class Params:
        rerank = factory.Trait(
            method=HTTPMethod.POST,
            endpoint="/rerank",
            model="BAAI/bge-reranker-v2-m3",
            body=factory.LazyFunction(
                lambda: {
                    "query": fake.sentence(),
                    "texts": fake.sentences(nb=fake.random_int(min=1, max=10)),
                    "raw_scores": False,
                    "return_text": False,
                }
            ),
        )


# Response factories
class TeiModelsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["is_rerank", "max_context_length"]

    _status_code = 200

    # parameters
    is_rerank = False
    max_context_length = factory.Faker("random_int", min=1024, max=8192)

    # body
    model_id = factory.Faker("bothify", text="????/???-?#")
    model_sha = None
    model_dtype = "float16"
    model_type = factory.LazyAttribute(lambda self: {"reranker": {"id2label": {"0": "LABEL_0"}, "label2id": {"LABEL_0": 0}}} if self.is_rerank else {"embedding": {"pooling": "cls"}})  # fmt: off
    max_concurrent_requests = factory.Faker("random_int", min=124, max=512)
    max_input_length = factory.LazyAttribute(lambda self: self.max_context_length)
    max_batch_tokens = factory.Faker("random_int", min=1024, max=16384)
    max_batch_requests = None
    max_client_batch_size = factory.Faker("random_int", min=16, max=64)
    auto_truncate = False
    tokenization_workers = 126
    version = "1.8.3"
    sha = "3120a50a84b22bb3cd84152c11d4373faea6d99a"
    docker_label = "sha-3120a50"


class TeiEmbeddingsResponseFactory(factory.DictFactory):
    class Meta:
        exclude = ["dimensions", "model_id"]

    _status_code = 200

    # parameters
    dimensions: int = 1024
    model_id = factory.Faker("bothify", text="????/???-?#")

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
    model = factory.LazyAttribute(lambda self: self.model_id)
    object = "list"
    usage = {"prompt_tokens": 6, "total_tokens": 6}


class TeiRerankResponseFactory(factory.Factory):
    class Meta:
        model = list
        inline_args = ("data",)
        exclude = ["raw_scores", "return_text", "count", "indices", "raw_data", "model_id"]

    _status_code = 200

    # parameters
    raw_scores = False
    return_text = False
    count = 3

    indices = factory.LazyAttribute(lambda self: random.sample(range(self.count), self.count))
    raw_data = factory.LazyAttribute(
        lambda self: [
            (idx, fake.pyfloat(min_value=0, max_value=1, right_digits=2), fake.pyfloat(min_value=0, max_value=10, right_digits=1), fake.sentence())
            for idx in self.indices
        ]
    )

    # body
    data = factory.LazyAttribute(
        lambda self: [
            {"index": idx, "score": raw_score if self.raw_scores else score, **({"text": text} if self.return_text else {})}
            for idx, score, raw_score, text in self.raw_data
        ]
    )


# Error response factories
class TeiNotEmbeddingModelResponseFactory(factory.DictFactory):
    _status_code = 424

    # body
    error = {
        "code": 424,
        "message": "Backend error: Model is not an embedding model",
        "type": "Backend",
    }
