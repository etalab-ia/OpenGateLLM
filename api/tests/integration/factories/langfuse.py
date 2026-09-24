from langfuse import Langfuse

from api.domain.provider.entities import ProviderEndpoint
from api.domain.usage.entities import EnvironmentalImpacts, PromptTokensDetails, Usage
from api.infrastructure.langfuse import LangfuseUsageRepository


def record_langfuse_usage(
    client: Langfuse,
    user_id: int,
    key_id: int = 7,
    endpoint: ProviderEndpoint = ProviderEndpoint.CHAT_COMPLETIONS,
    model: str = "chat-router",
    failed: bool = False,
    usage: Usage | None = None,
) -> str:
    """Write one request through the production write path: Langfuse has no transaction to seed rows into."""
    repository = LangfuseUsageRepository(client=client)
    request_id = repository.start_record(
        endpoint=endpoint,
        model=model,
        user_id=user_id,
        router_id=1,
        router_name=model,
        user_email=f"user-{user_id}@example.com",
        key_id=key_id,
        key_name=f"key-{key_id}",
    )
    if failed:
        repository.fail_record(message="TooBusyModelError", status_code=503)
    else:
        usage = usage or Usage(
            prompt_tokens=3,
            completion_tokens=5,
            total_tokens=8,
            prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
            cost=0.01,
            impacts=EnvironmentalImpacts(kWh=1.5, kgCO2eq=2.5),
        )
        repository.update_record(usage=usage, provider_id=1, provider_model_name=f"{model}-provider")
    repository.end_record()
    return request_id
