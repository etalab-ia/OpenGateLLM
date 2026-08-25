from dataclasses import dataclass
import datetime as dt

from api.domain.usage import UsageRepository
from api.domain.usage.entities import UsagePage


@dataclass
class GetUsagesCommand:
    user_id: int
    offset: int
    limit: int
    start_time: int | None
    end_time: int | None
    endpoint: str | None


@dataclass
class GetUsagesUseCaseSuccess:
    usage_page: UsagePage


type GetUsagesUseCaseResult = GetUsagesUseCaseSuccess


class GetUsagesUseCase:
    DEFAULT_LOOKBACK_DAYS = 30

    def __init__(self, usage_repository: UsageRepository):
        self.usage_repository = usage_repository

    async def execute(self, command: GetUsagesCommand) -> GetUsagesUseCaseResult:
        now = dt.datetime.now(tz=dt.UTC)
        start_time = (
            dt.datetime.fromtimestamp(command.start_time, tz=dt.UTC)
            if command.start_time is not None
            else now - dt.timedelta(days=self.DEFAULT_LOOKBACK_DAYS)
        )
        end_time = dt.datetime.fromtimestamp(command.end_time, tz=dt.UTC) if command.end_time is not None else now

        usage_page = await self.usage_repository.get_usages_page(
            user_id=command.user_id,
            start_time=start_time,
            end_time=end_time,
            offset=command.offset,
            limit=command.limit,
            endpoint=command.endpoint,
        )

        return GetUsagesUseCaseSuccess(usage_page=usage_page)
