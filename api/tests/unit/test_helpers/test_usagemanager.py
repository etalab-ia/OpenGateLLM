from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._usagemanager import UsageManager
from api.schemas.me.usage import EndpointUsage
from api.schemas.usage import EnvironmentalImpacts


class _Result:
    def __init__(self, all_rows=None):
        self._all_rows = all_rows

    def all(self):
        return self._all_rows or []


def _usage_row(
    *,
    kwh: float | None,
    kgco2eq: float | None,
    model: str = "model-a",
    key: str = "key-a",
    endpoint: str = EndpointUsage.CHAT_COMPLETIONS.value,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    total_tokens: int = 30,
    cost: float = 0.1,
    latency: int = 100,
    ttft: int = 50,
    created: int = 1_700_000_000,
):
    return SimpleNamespace(
        model=model,
        key=key,
        endpoint=endpoint,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        latency=latency,
        ttft=ttft,
        kwh=kwh,
        kgco2eq=kgco2eq,
        created=created,
    )


@pytest.fixture
def postgres_session():
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwh", "kgco2eq", "expected_impacts"),
    [
        (None, None, EnvironmentalImpacts(kWh=0.0, kgCO2eq=0.0)),
        (None, 1.5, EnvironmentalImpacts(kWh=0.0, kgCO2eq=1.5)),
        (2.5, None, EnvironmentalImpacts(kWh=2.5, kgCO2eq=0.0)),
        (2.5, 1.5, EnvironmentalImpacts(kWh=2.5, kgCO2eq=1.5)),
    ],
)
async def test_get_usages_maps_null_environmental_impacts_to_zero(
    postgres_session: AsyncSession,
    kwh: float | None,
    kgco2eq: float | None,
    expected_impacts: EnvironmentalImpacts,
):
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[_usage_row(kwh=kwh, kgco2eq=kgco2eq)]))

    usages = await UsageManager().get_usages(
        postgres_session=postgres_session,
        user_id=1,
        offset=0,
        limit=10,
        start_time=1_700_000_000,
        end_time=1_800_000_000,
    )

    assert len(usages) == 1
    assert usages[0].usage.impacts == expected_impacts
    assert usages[0].usage.impacts.kWh is not None
    assert usages[0].usage.impacts.kgCO2eq is not None
