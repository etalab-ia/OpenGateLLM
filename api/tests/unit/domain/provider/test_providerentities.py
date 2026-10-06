from unittest.mock import patch

import pytest

from api.domain.provider import ProviderReservationRefused
from api.domain.provider.entities import ProviderEndpoint, ProviderRequest
from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderReservationRefused:
    @pytest.mark.parametrize("retries", [None, 0])
    def test_should_return_one_second_when_retry_window_is_empty(self, retries):
        assert ProviderReservationRefused(total_load=4).retry_after(retries=retries) == 1

    def test_should_scale_retry_after_with_total_load(self):
        with patch("api.domain.provider._providerconcurrencylimiter.random.random", return_value=0.5):
            assert ProviderReservationRefused(total_load=2).retry_after(retries=10) == 3

    def test_should_clamp_retry_after_to_retry_window(self):
        with patch("api.domain.provider._providerconcurrencylimiter.random.random", return_value=0.99):
            assert ProviderReservationRefused(total_load=100).retry_after(retries=4) == 2


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None


class TestProviderRequest:
    def test_should_generate_request_id_when_omitted(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS)

        assert len(request.id) == 32
        assert request.id != ProviderRequest(endpoint=ProviderEndpoint.MODELS).id

    def test_should_keep_explicit_request_id(self):
        request = ProviderRequest(endpoint=ProviderEndpoint.MODELS, id="req-1")

        assert request.id == "req-1"
