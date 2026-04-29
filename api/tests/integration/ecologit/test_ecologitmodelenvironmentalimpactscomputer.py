import pytest

from api.domain.usage.entities import EnvironmentalImpacts
from api.infrastructure.ecologit._ecologitmodelenvironmentalimpactscomputer import EcologitModelEnvironmentalImpactsComputer
from api.schemas.admin.providers import ProviderCarbonFootprintZone


@pytest.fixture
def computer():
    return EcologitModelEnvironmentalImpactsComputer()


class TestEcologitModelEnvironmentalImpactsComputer:
    def test_returns_zero_impacts_when_model_active_params_is_zero(self, computer):
        # Act
        result = computer.compute(
            model_active_params=0,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=1000,
            request_latency=100,
        )

        # Assert
        assert result == EnvironmentalImpacts(kWh=0, kgCO2eq=0)

    def test_returns_zero_impacts_when_model_total_params_is_zero(self, computer):
        # Act
        result = computer.compute(
            model_active_params=7,
            model_total_params=0,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=1000,
            request_latency=100,
        )

        # Assert
        assert result == EnvironmentalImpacts(kWh=0, kgCO2eq=0)

    def test_returns_zero_impacts_when_completion_tokens_is_zero(self, computer):
        # Act
        result = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=0,
            request_latency=100,
        )

        # Assert
        assert result == EnvironmentalImpacts(kWh=0, kgCO2eq=0)

    def test_computes_impacts_when_all_params_are_valid(self, computer):
        # Act
        result = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=1000,
            request_latency=100,
        )

        # Assert
        assert result.kWh > 0
        assert result.kgCO2eq > 0

    def test_model_zone_is_taken_to_compute_impacts(self, computer):
        # Act
        result_wor = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=1000,
            request_latency=100,
        )
        result_fra = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.FRA,
            completion_tokens=1000,
            request_latency=100,
        )

        # Assert
        assert result_wor.kWh != result_fra.kWh or result_wor.kgCO2eq != result_fra.kgCO2eq

    def test_completion_tokens_is_taken_to_compute_impacts(self, computer):
        # Act
        result_low = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=100,
            request_latency=100,
        )
        result_high = computer.compute(
            model_active_params=7,
            model_total_params=7,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=1000,
            request_latency=100,
        )

        # Assert
        assert result_high.kWh > result_low.kWh
        assert result_high.kgCO2eq > result_low.kgCO2eq
