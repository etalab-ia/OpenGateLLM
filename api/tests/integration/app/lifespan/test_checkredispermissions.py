import logging

import pytest
import redis.asyncio as redis

from api.lifespan import check_redis_permissions


@pytest.mark.asyncio(loop_scope="session")
class TestCheckRedisPermissions:
    async def test_should_log_that_the_provider_limits_can_be_enforced_when_the_redis_user_may_run_every_command(self, test_redis_pool, caplog):
        # ACT
        with caplog.at_level(logging.INFO, logger="api.lifespan"):
            await check_redis_permissions(test_redis_pool)

        # ASSERT
        assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
            (logging.INFO, "Redis allows every command the provider limits need.")
        ]

    async def test_should_log_an_error_and_let_the_api_start_when_the_redis_user_is_denied_a_command(self, create_redis_user_url, caplog):
        # ARRANGE
        pool = redis.ConnectionPool.from_url(await create_redis_user_url(denied_command="time"))

        # ACT
        try:
            with caplog.at_level(logging.ERROR):
                await check_redis_permissions(pool)
        finally:
            await pool.aclose()

        # ASSERT
        assert [record.levelno for record in caplog.records] == [logging.ERROR]
        assert "The API starts without enforcing them" in caplog.records[0].getMessage()
        assert "'time'" in caplog.records[0].getMessage()
