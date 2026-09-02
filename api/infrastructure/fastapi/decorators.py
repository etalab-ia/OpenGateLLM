import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
from datetime import UTC, datetime
import functools
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.router import RouterRateLimiter
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.dependencies import request_context
from api.sql.models import Usage, User
from api.utils.configuration import configuration

logger = logging.getLogger(__name__)
PostgresSessionProvider = Callable[[], AsyncGenerator[AsyncSession | Any, Any]]
RouterRateLimiterProvider = Callable[[], RouterRateLimiter]


def _log_background_task_failure(task: asyncio.Task) -> None:
    if task.cancelled():
        return

    error = task.exception()
    if error is not None:
        logger.exception("Background hook task '%s' failed.", task.get_name(), exc_info=error)


def _schedule_background_task(coroutine: Coroutine, task_name: str) -> None:
    task = asyncio.create_task(coroutine, name=task_name)
    task.add_done_callback(_log_background_task_failure)


def _total_tokens(prompt_tokens: int | None, completion_tokens: int | None) -> int | None:
    if prompt_tokens is None and completion_tokens is None:
        return None
    return (prompt_tokens or 0) + (completion_tokens or 0)


def hooks(*, postgres_session_provider: PostgresSessionProvider, router_rate_limiter_provider: RouterRateLimiterProvider):
    def decorator(endpoint_func):
        @functools.wraps(endpoint_func)
        async def wrapper(*args, **kwargs):
            usage = Usage(created=datetime.now(tz=UTC), endpoint="N/A")
            context = request_context.get()
            if context.key is None:
                logger.info(f"No key found in request context, skipping usage logging ({context.endpoint}).")
                return await endpoint_func(*args, **kwargs)

            try:
                response = await endpoint_func(*args, **kwargs)
                usage.status = response.status_code
                return response

            except HTTPException as e:
                usage.status = e.status_code
                raise e

            finally:
                usage = set_usage_from_context(usage=usage)
                _schedule_background_task(
                    coroutine=charge_router_limits(user=context.user, usage=usage, router_rate_limiter_provider=router_rate_limiter_provider),
                    task_name="hooks-charge-router-limits",
                )
                _schedule_background_task(
                    coroutine=log_usage(usage=usage, postgres_session_provider=postgres_session_provider),
                    task_name="hooks-log-usage",
                )
                _schedule_background_task(
                    coroutine=update_budget(usage=usage, postgres_session_provider=postgres_session_provider),
                    task_name="hooks-update-budget",
                )

        return wrapper

    return decorator


def set_usage_from_context(usage: Usage):
    context = request_context.get()
    usage.user_id = context.key.user_id
    usage.user_email = context.user.email
    usage.token_id = context.key.id
    usage.token_name = context.key.name
    usage.endpoint = context.endpoint
    usage.method = context.method
    usage.router_id = context.router_id
    usage.provider_id = context.provider_id
    usage.router_name = context.router_name
    usage.provider_model_name = context.provider_model_name
    usage.prompt_tokens = context.prompt_tokens
    usage.completion_tokens = context.completion_tokens
    usage.total_tokens = _total_tokens(context.prompt_tokens, context.completion_tokens)
    usage.cost = context.cost
    usage.kwh = context.kwh
    usage.kgco2eq = context.kgco2eq

    return usage


async def charge_router_limits(user: AuthenticatedUserView | None, usage: Usage, router_rate_limiter_provider: RouterRateLimiterProvider):
    if user is None or user.is_admin:
        return
    if usage.router_id is None:
        return

    router_limits = [limit for limit in user.limits if limit.router_id == usage.router_id]
    try:
        router_rate_limiter = router_rate_limiter_provider()
        await router_rate_limiter.update_rate_limit_state(
            user_id=user.id,
            router_limits=router_limits,
            router_id=usage.router_id,
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
        )
    except Exception:
        logger.exception("Unexpected failure during rate limit state update for user %s.", user.id)


async def log_usage(usage: Usage, postgres_session_provider: PostgresSessionProvider):
    if configuration.settings.monitoring_postgres_enabled is False:
        return

    try:
        async for postgres_session in postgres_session_provider():
            postgres_session.add(usage)
            try:
                await postgres_session.commit()
            except Exception as e:
                logger.error(f"Failed to log usage: {e}")
                await postgres_session.rollback()
    except RuntimeError as e:
        logger.warning("Skipping usage logging because postgres session is unavailable: %s", e)
    except Exception:
        logger.exception("Unexpected failure during usage logging.")


async def update_budget(usage: Usage, postgres_session_provider: PostgresSessionProvider):
    if usage.cost is None or usage.cost == 0:
        return

    user_id = usage.user_id
    cost = usage.cost

    if not user_id:
        logger.warning("No user_id found in usage object for budget update")
        return
    try:
        async for postgres_session in postgres_session_provider():
            try:
                async with postgres_session.begin():
                    # Use SELECT FOR UPDATE to lock the user row during the transaction. This prevents concurrent modifications to the budget
                    select_stmt = select(User.budget).where(User.id == user_id).with_for_update()
                    result = await postgres_session.execute(select_stmt)
                    current_budget = result.scalar_one_or_none()

                    if current_budget is None or current_budget == 0:
                        return

                    actual_cost = min(cost, current_budget)
                    new_budget = round(current_budget - actual_cost, ndigits=6)

                    update_stmt = update(User).where(User.id == user_id).values(budget=new_budget, updated=func.now()).returning(User.budget)

                    await postgres_session.execute(update_stmt)

            except Exception as e:
                logger.exception(f"Failed to update budget for user {user_id}: {e}")
                return
    except RuntimeError as e:
        logger.warning("Skipping budget update because postgres session is unavailable: %s", e)
    except Exception:
        logger.exception("Unexpected failure during budget update for user %s.", user_id)
