from datetime import UTC, datetime
from uuid import uuid4

from langfuse import Langfuse

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage, UsageRecord
from api.infrastructure.langfuse import LangfuseUsageRepository


async def record_langfuse_usage(
    client: Langfuse,
    user_id: int,
    key_id: int = 7,
    endpoint: ProviderEndpoint = ProviderEndpoint.CHAT_COMPLETIONS,
    model: str = "chat-router",
    failed: bool = False,
    usage: Usage | None = None,
) -> str:
    """Write one request through the production write path: Langfuse has no transaction to seed rows into."""
    record = UsageRecord(
        request_id=uuid4().hex,
        endpoint=f"/v1{endpoint}",
        created=datetime.now(tz=UTC),
        user_id=user_id,
        user_email=f"user-{user_id}@example.com",
        key_id=key_id,
        key_name=f"key-{key_id}",
        router_id=1,
        router_name=model,
    )
    if failed:
        record.status = 503
        record.error = "TooBusyModelError"
    else:
        record.status = 200
        record.provider_id = 1
        record.provider_model_name = f"{model}-provider"
        record.usage = usage or Usage(
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
            prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
            cost=0.01,
            impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
        )

    repository = LangfuseUsageRepository(client=client)
    repository.open_record(record)
    await repository.save_record(record)

    return record.request_id
