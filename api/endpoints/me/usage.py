from fastapi import APIRouter, Depends, Query, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._usagemanager import UsageManager
from api.schemas.me.usage import EndpointUsage, Usages
from api.utils.context import request_context
from api.utils.dependencies import get_postgres_session, get_usage_manager
from api.utils.variables import ENDPOINT__ME_USAGE, ROUTER__ME

router = APIRouter(prefix="/v1", tags=[ROUTER__ME.title()])


@router.get(path=ENDPOINT__ME_USAGE, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Usages)
async def get_usage(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the usages to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the usages to get."),
    start_time: int | None = Query(default=None, description="Start time as Unix timestamp (if not provided, will be set to 30 days ago)"),
    end_time: int | None = Query(default=None, description="End time as Unix timestamp (if not provided, will be set to now)"),
    endpoint: EndpointUsage | None = Query(default=None, description="The endpoint to get usage for."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    usage_manager: UsageManager = Depends(get_usage_manager),
) -> JSONResponse:
    """
    Get usage for the current user.
    """
    usage = await usage_manager.get_usages(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        offset=offset,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        endpoint=endpoint,
    )

    return JSONResponse(content=Usages(data=usage).model_dump(), status_code=200)
