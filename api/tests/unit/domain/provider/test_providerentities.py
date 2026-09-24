from unittest.mock import patch

import pytest

from api.domain.provider import ProviderAdmissionFull
from api.domain.provider.entities import ProviderRequest
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


class TestProviderAdmissionFull:
    @pytest.mark.parametrize("retries", [None, 0])
    def test_should_return_one_second_when_retry_window_is_empty(self, retries):
        assert ProviderAdmissionFull(depth=4).retry_after(retries=retries) == 1

    def test_should_scale_retry_after_with_depth(self):
        with patch("api.domain.provider._providerqos.random.random", return_value=0.5):
            assert ProviderAdmissionFull(depth=2).retry_after(retries=10) == 3

    def test_should_clamp_retry_after_to_retry_window(self):
        with patch("api.domain.provider._providerqos.random.random", return_value=0.99):
            assert ProviderAdmissionFull(depth=100).retry_after(retries=4) == 2


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None


class TestProviderRequest:
    def test_should_generate_request_id_when_omitted(self):
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)

        assert request.id.startswith("request-")
        assert request.id != ProviderRequest(endpoint=EndpointRoute.MODELS).id

    def test_should_keep_explicit_request_id(self):
        request = ProviderRequest(endpoint=EndpointRoute.MODELS, id="req-1")

        assert request.id == "req-1"
