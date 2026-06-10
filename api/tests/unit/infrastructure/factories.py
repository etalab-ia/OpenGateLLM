from http import HTTPMethod
import random
from urllib.parse import urljoin

import factory
from faker import Faker
from openai.types import Embedding

from api.domain.embeddings.entities import CreateEmbeddingsBody, Embeddings
from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest
from api.domain.rerank.entities import CreateRerankBody, Rerank, RerankResult
from api.utils.variables import EndpointRoute

fake = Faker()


def _random_embeddings_input() -> list[int] | list[list[int]] | str | list[str]:
    return random.choice(
        [
            fake.sentences(nb=random.randint(1, 10)),
            fake.sentence(),
            fake.pylist(value_types=[int], variable_nb_elements=True),
            [fake.pylist(value_types=[int], variable_nb_elements=True) for _ in range(random.randint(1, 3))],
        ]
    )


class ProviderOriginalRequestFactory(factory.Factory):
    class Meta:
        model = ProviderOriginalRequest

    endpoint = factory.Faker("random_element", elements=list(EndpointRoute))
    body = None
    form = None
    files = None

    class Params:
        embeddings = factory.Trait(
            endpoint=EndpointRoute.EMBEDDINGS,
            body=factory.LazyAttribute(
                lambda self: CreateEmbeddingsBody(
                    model="openweight-embeddings",
                    input=_random_embeddings_input(),
                    dimensions=1536,
                    encoding_format="float",
                )
            ),
        )
        models = factory.Trait(endpoint=EndpointRoute.MODELS)
        rerank = factory.Trait(
            endpoint=EndpointRoute.RERANK,
            body=factory.LazyAttribute(
                lambda self: CreateRerankBody(
                    model="openweight-rerank",
                    query=fake.sentence(),
                    documents=fake.sentences(nb=3),
                    top_n=2,
                )
            ),
        )


class ProviderFormattedRequestFactory(factory.Factory):
    class Meta:
        model = ProviderFormattedRequest
        exclude = ["base_url"]

    base_url = "https://provider.test/"

    method = factory.Faker("random_element", elements=list(HTTPMethod))
    url = factory.LazyAttribute(lambda self: urljoin(self.base_url, "/"))
    body = factory.LazyFunction(dict)
    form = factory.LazyFunction(dict)
    files = factory.LazyFunction(dict)

    class Params:
        vllm_models = factory.Trait(
            method=HTTPMethod.GET,
            url=factory.LazyAttribute(lambda self: urljoin(self.base_url, "/v1/models")),
            body=factory.LazyFunction(dict),
        )
        vllm_embeddings = factory.Trait(
            method=HTTPMethod.POST,
            url=factory.LazyAttribute(lambda self: urljoin(self.base_url, "/v1/embeddings")),
            body=factory.LazyFunction(
                lambda: {
                    "model": "openweight-embeddings",
                    "input": ["hello world"],
                }
            ),
        )


class ProviderEmbeddingsFormattedResponseFactory(factory.Factory):
    class Meta:
        model = ProviderFormattedResponse

    dimensions = factory.Faker("random_int", min=1, max=1024)

    data = factory.LazyAttribute(
        lambda self: Embeddings(
            id=f"request-{fake.uuid4().replace('-', '')}",
            model="openweight-embeddings",
            data=[
                Embedding(
                    embedding=[fake.pyfloat(min_value=-1, max_value=1, right_digits=6) for _ in range(self.dimensions)],
                    index=0,
                    object="embedding",
                )
            ],
        )
    )


class ProviderModelResponseFactory(factory.Factory):
    class Meta:
        model = Model

    id = factory.Faker("bothify", text="model-????-####")
    object = "model"
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    owned_by = factory.Faker("company")
    max_context_length = factory.Faker("random_int", min=64000, max=245600)
    aliases = factory.LazyFunction(lambda: [fake.bothify(text="model-????-latest")])
    type = factory.Faker("random_element", elements=list(ModelType))


class ProviderModelsFormattedResponseFactory(factory.Factory):
    class Meta:
        model = ProviderFormattedResponse
        exclude = ["count"]

    count: int = 1

    data = factory.LazyAttribute(lambda self: Models(data=[ProviderModelResponseFactory() for _ in range(self.count)]))


class ProviderRerankFormattedResponseFactory(factory.Factory):
    class Meta:
        model = ProviderFormattedResponse

    data = factory.LazyAttribute(
        lambda self: Rerank(
            id=f"request-{fake.uuid4().replace('-', '')}",
            model="openweight-rerank",
            results=[
                RerankResult(index=index, relevance_score=score)
                for index, score in zip(
                    fake.pylist(value_types=[int], variable_nb_elements=True), fake.pylist(value_types=[float], variable_nb_elements=True)
                )
            ],
        )
    )
