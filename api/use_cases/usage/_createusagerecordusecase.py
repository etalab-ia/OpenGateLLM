from dataclasses import dataclass

from api.domain import UtcDatetime
from api.domain.usage import UsageRepository
from api.domain.usage.entities import UsageRecord


@dataclass
class CreateUsageRecordCommand:
    created: UtcDatetime
    endpoint: str
    method: str | None = None
    user_id: int | None = None
    user_email: str | None = None
    key_id: int | None = None
    key_name: str | None = None
    router_id: int | None = None
    router_name: str | None = None
    provider_id: int | None = None
    provider_model_name: str | None = None
    status: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    kwh: float | None = None
    kgco2eq: float | None = None
    latency: int | None = None
    ttft: int | None = None


@dataclass
class CreateUsageRecordUseCaseSuccess:
    usage_record: UsageRecord


type CreateUsageRecordUseCaseResult = CreateUsageRecordUseCaseSuccess


class CreateUsageRecordUseCase:
    def __init__(self, usage_repository: UsageRepository):
        self.usage_repository = usage_repository

    async def execute(self, command: CreateUsageRecordCommand) -> CreateUsageRecordUseCaseResult:
        usage_record = UsageRecord(
            created=command.created,
            endpoint=command.endpoint,
            method=command.method,
            user_id=command.user_id,
            user_email=command.user_email,
            key_id=command.key_id,
            key_name=command.key_name,
            router_id=command.router_id,
            router_name=command.router_name,
            provider_id=command.provider_id,
            provider_model_name=command.provider_model_name,
            status=command.status,
            prompt_tokens=command.prompt_tokens,
            completion_tokens=command.completion_tokens,
            cost=command.cost,
            kwh=command.kwh,
            kgco2eq=command.kgco2eq,
            latency=command.latency,
            ttft=command.ttft,
        )

        usage_record = await self.usage_repository.create_usage_record(usage_record=usage_record)

        return CreateUsageRecordUseCaseSuccess(usage_record=usage_record)
