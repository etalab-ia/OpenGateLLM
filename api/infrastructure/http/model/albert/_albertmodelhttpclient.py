from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import ModelHttpClient


class AlbertModelHttpClient(ModelHttpClient):
    TYPE = ProviderType.ALBERT
