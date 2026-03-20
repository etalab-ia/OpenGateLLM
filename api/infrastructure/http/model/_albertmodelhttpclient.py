from api.domain.provider.entities import ProviderType

from ._modelhttpclient import ModelHttpClient


class AlbertModelHttpClient(ModelHttpClient):
    TYPE = ProviderType.ALBERT
