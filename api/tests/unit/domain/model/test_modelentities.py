import pytest

from api.domain.model.entities import HealthStatus
from api.tests.unit.use_case.factories import ProviderFactory


class TestHealthStatusOfProvider:
    @pytest.mark.parametrize(
        "is_live,load,qos_limit,expected_status",
        [
            pytest.param(False, 0, 20, HealthStatus.RED, id="not_live"),
            pytest.param(True, 0, 0, HealthStatus.RED, id="closed"),
            pytest.param(True, 20, 20, HealthStatus.RED, id="load_at_the_limit"),
            pytest.param(True, 19, 20, HealthStatus.YELLOW, id="load_at_95_percent_of_the_limit"),
            pytest.param(True, 18, 20, HealthStatus.GREEN, id="load_below_95_percent_of_the_limit"),
            pytest.param(True, 1000, None, HealthStatus.GREEN, id="no_limit"),
            pytest.param(True, None, 20, HealthStatus.GREEN, id="load_unreadable"),
            pytest.param(True, None, 0, HealthStatus.RED, id="load_unreadable_and_closed"),
        ],
    )
    def test_should_compute_the_status_from_liveness_load_and_limit(self, is_live, load, qos_limit, expected_status):
        provider = ProviderFactory(qos_limit=qos_limit)

        status = HealthStatus.of_provider(provider=provider, is_live=is_live, load=load)

        assert status == expected_status


class TestHealthStatusBestOf:
    @pytest.mark.parametrize(
        "statuses,expected_status",
        [
            pytest.param([HealthStatus.RED, HealthStatus.GREEN], HealthStatus.GREEN, id="one_green"),
            pytest.param([HealthStatus.RED, HealthStatus.YELLOW], HealthStatus.YELLOW, id="yellow_and_red"),
            pytest.param([HealthStatus.RED, HealthStatus.RED], HealthStatus.RED, id="all_red"),
        ],
    )
    def test_should_return_the_most_available_status(self, statuses, expected_status):
        assert HealthStatus.best_of(statuses) == expected_status
