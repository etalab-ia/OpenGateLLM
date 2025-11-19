import asyncio
from datetime import datetime
import functools
import logging

from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select, update
from starlette.responses import StreamingResponse

from api.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from api.sql.models import Usage, User
from api.utils.configuration import configuration
from api.utils.context import request_context
from api.utils.dependencies import get_postgres_session

logger = logging.getLogger(__name__)


def hooks(func):
    """
    Extracts usage information from the request and response and logs it to the database.
    This decorator is designed to be used with FastAPI endpoints.
    It captures the request method, endpoint, user ID, token ID, model name, prompt tokens,
    completion tokens, and the duration of the request.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        usage = Usage(created=datetime.now(), endpoint="N/A")

        # get the request context (initial values)
        context = request_context.get()
        if context.user_info is None:
            logger.info(f"No user ID found in request, skipping usage logging ({context.endpoint}).")
            return await func(*args, **kwargs)
        if context.user_info.id == 0:
            logger.info(f"Master user ID found in request, skipping usage logging ({context.endpoint}).")
            return await func(*args, **kwargs)

        # find the request object
        request = next((arg for arg in args if isinstance(arg, Request)), None)
        if not request:
            request = kwargs.get("request", None)
        if not request:
            raise Exception("No request found in args or kwargs")

        # extract usage from response
        response = None  # initialize in case of early exception not from func
        try:
            # call the endpoint
            response = await func(*args, **kwargs)

            if isinstance(response, StreamingResponse):
                return wrap_streaming_response(response=response, usage=usage)

            else:
                return wrap_unstreaming_response(response=response, usage=usage)

        except HTTPException as e:
            usage = set_usage_from_context(usage=usage)
            usage.status = e.status_code
            asyncio.create_task(log_usage(usage=usage))
            raise e  # Re-raise the exception for FastAPI to handle

    return wrapper


def set_usage_from_context(usage: Usage):
    context = request_context.get()
    usage.user_id = context.user_info.id
    usage.user_email = context.user_info.email
    usage.token_id = context.key_id
    usage.token_name = context.key_name
    usage.endpoint = context.endpoint
    usage.method = context.method
    usage.router_id = context.router_id
    usage.provider_id = context.provider_id
    usage.router_name = context.router_name
    usage.provider_model_name = context.provider_model_name
    usage.prompt_tokens = context.usage.prompt_tokens
    usage.completion_tokens = context.usage.completion_tokens
    usage.total_tokens = context.usage.total_tokens
    usage.cost = context.usage.cost
    usage.kwh_min = context.usage.carbon.kWh.min
    usage.kwh_max = context.usage.carbon.kWh.max
    usage.kgco2eq_min = context.usage.carbon.kgCO2eq.min
    usage.kgco2eq_max = context.usage.carbon.kgCO2eq.max
    usage.ttft = context.ttft
    usage.latency = context.latency

    return usage


def wrap_unstreaming_response(response: Response, usage: Usage) -> Response:
    """
    Wrap a non-streaming response to capture the final status code and log usage.
    Usage data is already populated from request_context, so no parsing is needed.
    """

    usage = set_usage_from_context(usage=usage)
    usage.status = response.status_code

    asyncio.create_task(log_usage(usage=usage))
    asyncio.create_task(update_budget(usage=usage))

    return response


def wrap_streaming_response(response: StreamingResponse, usage: Usage) -> StreamingResponseWithStatusCode:
    """
    Wrap a streaming response to capture the final status code and log usage.
    Usage data is already populated from request_context, so no parsing is needed.
    """
    original_stream = response.body_iterator

    async def wrapped_stream():
        nonlocal usage
        response_status_code = None

        try:
            async for chunk in original_stream:
                if isinstance(chunk, tuple):
                    response_status_code = chunk[1]

                yield chunk
        finally:
            if response_status_code is not None:
                usage.status = response_status_code

            usage = set_usage_from_context(usage=usage)

            print("write streaming response to database")

            asyncio.create_task(log_usage(usage=usage))
            asyncio.create_task(update_budget(usage=usage))

    return StreamingResponseWithStatusCode(wrapped_stream(), media_type=response.media_type)


async def log_usage(usage: Usage):
    """
    Logs the usage information to the database.
    This function captures the duration of the request and sets the status code of the response if available.
    """

    if configuration.settings.monitoring_postgres_enabled is False:
        return

    async for postgres_session in get_postgres_session():
        postgres_session.add(usage)
        try:
            await postgres_session.commit()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await postgres_session.rollback()


async def update_budget(usage: Usage):
    """
    Updates the budget of the user by decreasing it by the calculated cost.
    Retrieves the current user budget, and decreases it by min(usage.budget, current_budget_value).
    Uses row-level locking to prevent concurrency issues.
    """
    # Check if there's a budget cost to deduct
    if usage.cost is None or usage.cost == 0:
        return

    user_id = usage.user_id
    cost = usage.cost

    if not user_id:
        logger.warning("No user_id found in usage object for budget update")
        return

    # Decrease the user's budget by the calculated cost with proper locking
    async for postgres_session in get_postgres_session():
        try:
            async with postgres_session.begin():
                # Use SELECT FOR UPDATE to lock the user row during the transaction. This prevents concurrent modifications to the budget
                select_stmt = select(User.budget).where(User.id == user_id).with_for_update()
                result = await postgres_session.execute(select_stmt)
                current_budget = result.scalar_one_or_none()

                if current_budget is None or current_budget == 0:
                    return

                # Calculate the actual cost to deduct (minimum of requested cost and available budget)
                actual_cost = min(cost, current_budget)
                new_budget = round(current_budget - actual_cost, ndigits=6)

                # Update the budget
                update_stmt = update(User).where(User.id == user_id).values(budget=new_budget, updated=func.now()).returning(User.budget)

                result = await postgres_session.execute(update_stmt)

        except Exception as e:
            logger.exception(f"Failed to update budget for user {user_id}: {e}")
            return
