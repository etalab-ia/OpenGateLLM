import pytest
from redis.asyncio import Redis as AsyncRedis

from api.infrastructure.redis._redisauthssoprovidercache import RedisAuthSsoProviderCache

ISSUER_URL = "https://issuer.example.com"
JWKS = {"keys": [{"kid": "test-kid"}]}


@pytest.fixture
def cache(redis_client):
    return RedisAuthSsoProviderCache(redis_client=redis_client)


@pytest.mark.asyncio(loop_scope="session")
class TestRedisAuthSsoProviderCache:
    async def test_get_returns_none_when_key_missing(self, cache: RedisAuthSsoProviderCache):
        # Act
        result = await cache.get(email=ISSUER_URL)

        # Assert
        assert result is None

    async def test_set_and_get_returns_claims(self, cache: RedisAuthSsoProviderCache):
        # Arrange
        claims = JWKS

        # Act
        await cache.set(email=ISSUER_URL, claims=claims, expire=600)
        result = await cache.get(email=ISSUER_URL)

        # Assert
        assert result == claims

    async def test_set_overwrites_existing_claims(self, cache: RedisAuthSsoProviderCache):
        # Arrange
        initial_claims = JWKS
        updated_claims = {"keys": [{"kid": "other-kid"}]}
        await cache.set(email=ISSUER_URL, claims=initial_claims, expire=600)

        # Act
        await cache.set(email=ISSUER_URL, claims=updated_claims, expire=600)
        result = await cache.get(email=ISSUER_URL)

        # Assert
        assert result == updated_claims

    async def test_delete_removes_cached_claims(self, cache: RedisAuthSsoProviderCache, redis_client: AsyncRedis):
        # Arrange
        await cache.set(email=ISSUER_URL, claims=JWKS, expire=600)
        assert await redis_client.get(ISSUER_URL) is not None

        # Act
        await cache.delete(email=ISSUER_URL)
        result = await cache.get(email=ISSUER_URL)

        # Assert
        assert await redis_client.get(ISSUER_URL) is None
        assert result is None

    async def test_set_stores_value_with_expiration(self, cache: RedisAuthSsoProviderCache, redis_client: AsyncRedis):
        # Arrange
        expire = 120

        # Act
        await cache.set(email=ISSUER_URL, claims=JWKS, expire=expire)
        ttl = await redis_client.ttl(ISSUER_URL)

        # Assert
        assert 0 < ttl <= expire
