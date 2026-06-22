import json

from redis.asyncio import Redis as AsyncRedis

from api.domain.auth import AuthSsoProviderCache


class RedisAuthSsoProviderCache(AuthSsoProviderCache):
    def __init__(self, redis_client: AsyncRedis):
        self.redis_client = redis_client

    async def get(self, email: str) -> dict | None:
        value = await self.redis_client.get(email)
        if value is None:
            return None
        return json.loads(value)

    async def set(self, email: str, claims: dict, expire: int = 600) -> None:
        await self.redis_client.set(name=email, value=json.dumps(claims), ex=expire)

    async def delete(self, email: str) -> None:
        await self.redis_client.delete(email)
