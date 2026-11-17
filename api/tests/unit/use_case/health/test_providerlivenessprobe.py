from unittest.mock import create_autospec

import pytest

from api.domain.model.errors import StatusCodeModelError
from api.domain.provider import ProviderClient
from api.domain.provider.entities import ProviderEndpoint, ProviderModels, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.tests.unit.use_case.factories import ProviderFactory
from api.use_cases.health import ProviderLivenessProbe


@pytest.fixture
def mock_provider_client():
    return create_autospec(ProviderClient, instance=True, spec_set=True)


@pytest.fixture
def probe(mock_provider_client) -> ProviderLivenessProbe:
    return ProviderLivenessProbe(provider_client=mock_provider_client)


class TestProviderLivenessProbe:
    @pytest.mark.asyncio
    async def test_should_be_live_when_the_provider_answers_its_models_endpoint(self, probe, mock_provider_client):
        # Arrange
        provider = ProviderFactory(timeout=300)
        mock_provider_client.forward.return_value = ProviderResponse(data=ProviderModels(data=[]))

        # Act
        is_live = await probe.is_live(provider=provider)

        # Assert
        assert is_live is True
        mock_provider_client.forward.assert_awaited_once()
        assert mock_provider_client.forward.await_args.kwargs["provider"] == provider.with_timeout(ProviderLivenessProbe.TIMEOUT_SECONDS)
        assert mock_provider_client.forward.await_args.kwargs["request"].endpoint == ProviderEndpoint.MODELS

    @pytest.mark.asyncio
    async def test_should_be_live_when_the_models_response_cannot_be_parsed(self, probe, mock_provider_client):
        # Arrange
        provider = ProviderFactory()
        mock_provider_client.forward.return_value = ProviderAdapterValidationResponseError(provider_type=provider.type, errors=[{"msg": "invalid"}])

        # Act
        is_live = await probe.is_live(provider=provider)

        # Assert
        assert is_live is True

    @pytest.mark.asyncio
    async def test_should_not_be_live_when_the_models_request_fails(self, probe, mock_provider_client):
        # Arrange
        mock_provider_client.forward.return_value = StatusCodeModelError(status_code=500, detail="error")

        # Act
        is_live = await probe.is_live(provider=ProviderFactory())

        # Assert
        assert is_live is False
