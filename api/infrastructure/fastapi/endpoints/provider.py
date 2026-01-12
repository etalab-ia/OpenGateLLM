# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from redis.asyncio import Redis as AsyncRedis
# from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context, get_model_provider_factory
#
# router = APIRouter(prefix="/v1", tags=["model-requests"])
# class ForwardRequest(BaseModel):
#     """Request to forward to a model provider."""
#
#     provider_id: int
#     messages: list[dict[str, str]]
#     stream: bool = False
#     temperature: float = 0.7
#     max_tokens: int | None = None
#
#
# @router.post("/forward")
# async def forward_to_provider(
#     request: ForwardRequest,
#     postgres_session: AsyncSession = Depends(get_postgres_session),
#     redis_client: AsyncRedis = Depends(get_redis_client),
#     factory=Depends(get_model_provider_factory),
# ):
#     from api.sql.models import Provider as ProviderTable
#     from sqlalchemy import select
#
#     query = select(ProviderTable).where(ProviderTable.id == request.provider_id)
#     result = await postgres_session.execute(query)
#     provider_config = result.scalar_one_or_none()
#
#     if not provider_config:
#         raise HTTPException(status_code=404, detail=f"Provider {request.provider_id} not found")
#
#     provider = factory.create(
#         provider_type=ProviderType(provider_config.type),
#         url=provider_config.url,
#         key=provider_config.key,
#         timeout=provider_config.timeout,
#         model_name=provider_config.model_name,
#         model_carbon_footprint_zone=provider_config.model_carbon_footprint_zone,
#         model_carbon_footprint_total_params=provider_config.model_carbon_footprint_total_params,
#         model_carbon_footprint_active_params=provider_config.model_carbon_footprint_active_params,
#     )
#
#     # Set provider metadata (from ModelRegistry pattern)
#     provider.id = provider_config.id
#
#     # 3. Forward request to provider
#     try:
#         if request.stream:
#             # Streaming response
#             return provider.forward_stream(
#                 method="POST",
#                 endpoint="/v1/chat/completions",
#                 redis_client=redis_client,
#                 json={
#                     "messages": request.messages,
#                     "stream": True,
#                     "temperature": request.temperature,
#                     "max_tokens": request.max_tokens,
#                 },
#             )
#         else:
#             # Non-streaming response
#             response = await provider.forward_request(
#                 method="POST",
#                 endpoint="/v1/chat/completions",
#                 redis_client=redis_client,
#                 json={
#                     "messages": request.messages,
#                     "stream": False,
#                     "temperature": request.temperature,
#                     "max_tokens": request.max_tokens,
#                 },
#             )
#
#             return response.json()
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Provider error: {str(e)}")
