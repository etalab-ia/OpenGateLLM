from dataclasses import dataclass
import datetime as dt

from api.domain.usage import UsageRepository
from api.domain.usage.entities import UsageBucketPage


@dataclass
class GetUsagesCommand:
    user_id: int
    offset: int
    limit: int
    start_time: int
    end_time: int
    endpoint: str | None
    models: list[str] | None
    key_id: int | None


@dataclass
class GetUsagesUseCaseSuccess:
    usage_page: UsageBucketPage


type GetUsagesUseCaseResult = GetUsagesUseCaseSuccess


class GetUsagesUseCase:
    def __init__(self, usage_repository: UsageRepository):
        self.usage_repository = usage_repository

    async def execute(self, command: GetUsagesCommand) -> GetUsagesUseCaseResult:
        start_time = dt.datetime.fromtimestamp(command.start_time, tz=dt.UTC)
        end_time = dt.datetime.fromtimestamp(command.end_time, tz=dt.UTC)

        usage_page = await self.usage_repository.get_usage_buckets_page(
            user_id=command.user_id,
            start_time=start_time,
            end_time=end_time,
            offset=command.offset,
            limit=command.limit,
            endpoint=command.endpoint,
            models=command.models,
            key_id=command.key_id,
        )

        return GetUsagesUseCaseSuccess(usage_page=usage_page)
