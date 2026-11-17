from api.domain.provider import ProviderClient
from api.domain.provider.entities import Provider, ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError


class ProviderLivenessProbe:
    TIMEOUT_SECONDS = 4

    def __init__(self, provider_client: ProviderClient):
        self.provider_client = provider_client

    async def is_live(self, provider: Provider) -> bool:
        response = await self.provider_client.forward(
            provider=provider.with_timeout(self.TIMEOUT_SECONDS),
            request=ProviderRequest(endpoint=ProviderEndpoint.MODELS),
        )
        match response:
            # an unparsable payload still proves the provider answered
            case ProviderResponse() | ProviderAdapterValidationResponseError():
                return True
            case _:
                return False
