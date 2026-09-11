from pydantic import ValidationError
import pytest

from api.tests.unit.use_case.factories import ProviderFactory


class TestProviderQoSLimit:
    def test_should_replace_qos_limit(self):
        provider = ProviderFactory(qos_limit=None)

        updated_provider = provider.with_qos_limit(4)

        assert updated_provider.qos_limit == 4
        assert provider.qos_limit is None

    def test_should_reject_negative_qos_limit(self):
        with pytest.raises(ValidationError):
            ProviderFactory(qos_limit=-1)
