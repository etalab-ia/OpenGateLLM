from api.utils.variables import PREFIX__REDIS_METRIC_GAUGE


class MetricsRedisFactory:
    @classmethod
    async def set_inflight(cls, redis_client, provider_id: int, value: int = 1) -> str:
        key = f"{PREFIX__REDIS_METRIC_GAUGE}:inflight:{provider_id}"
        await redis_client.set(key, value)

        return key
