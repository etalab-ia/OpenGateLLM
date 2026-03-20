from http import HTTPMethod

import factory
from faker import Faker

from api.infrastructure.http.model import FormattedModelRequest, OriginalModelResponse
from api.tests.unit.infrastructure.http.factories.common import RERANK_DOCUMENTS_COUNT

fake = Faker()


# Formatted request factories
class TeiFormattedModelRequestFactory(factory.DictFactory):
    class Meta:
        model = FormattedModelRequest

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    endpoint = factory.Faker("url")
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
                    "texts": fake.sentences(nb=RERANK_DOCUMENTS_COUNT),
                    "raw_scores": False,
                    "return_text": False,
                }
            ),
        )


# Original response factories
class TeiRerankOriginalResponseFactory(factory.Factory):
    class Meta:
        model = OriginalModelResponse
        exclude = ["use_raw_scores", "use_return_text"]

    use_raw_scores = False
    use_return_text = False

    data = factory.LazyAttribute(
        lambda self: [
            {
                "index": idx,
                "score": raw_score if self.use_raw_scores else score,
                **({"text": text} if self.use_return_text else {}),
            }
            for idx, score, raw_score, text in [
                (2, 0.95, 9.5, fake.sentence()),
                (0, 0.72, 7.2, fake.sentence()),
                (1, 0.31, 3.1, fake.sentence()),
            ]
        ]
    )
    latency = 100


class TeiModelsOriginalResponseFactory(factory.Factory):
    class Meta:
        model = OriginalModelResponse
        exclude = ["is_rerank"]

    is_rerank = False

    data = factory.LazyAttribute(
        lambda self: {
            "model_id": "BAAI/bge-reranker-v2-m3" if self.is_rerank else "BAAI/bge-m3",
            "model_sha": None,
            "model_dtype": "float16",
            "model_type": (
                {"reranker": {"id2label": {"0": "LABEL_0"}, "label2id": {"LABEL_0": 0}}} if self.is_rerank else {"embedding": {"pooling": "cls"}}
            ),
            "max_concurrent_requests": 512,
            "max_input_length": 8192,
            "max_batch_tokens": 16384,
            "max_batch_requests": None,
            "max_client_batch_size": 64,
            "auto_truncate": False,
            "tokenization_workers": 126,
            "version": "1.8.3",
            "sha": "3120a50a84b22bb3cd84152c11d4373faea6d99a",
            "docker_label": "sha-3120a50",
        }
    )


class TeiOriginalResponseFactory:
    def __new__(cls, rerank=False, models=False, raw_scores=False, return_text=False, **kwargs):
        if rerank:
            return TeiRerankOriginalResponseFactory(use_raw_scores=raw_scores, use_return_text=return_text, **kwargs)
        if models:
            return TeiModelsOriginalResponseFactory(**kwargs)
        return OriginalModelResponse()
