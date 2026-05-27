from http import HTTPMethod
from urllib.parse import urljoin

import factory
from faker import Faker

from api.domain.embeddings.entities import CreateEmbeddingsBody
from api.domain.provider.entities import ProviderFormattedRequest, ProviderOriginalRequest
from api.domain.rerank.entities import CreateRerankBody
from api.utils.variables import EndpointRoute

fake = Faker()


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
                CreateEmbeddingsBody(
                    model="openweight-embeddings",
                    input=fake.sentences(nb=3),
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
