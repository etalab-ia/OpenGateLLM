from contextvars import ContextVar
import logging

from fastapi import Depends, Query, Security

from api.dependencies import get_keys_use_case_factory
from api.domain import SortField, SortOrder
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_request_context
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException
from api.infrastructure.fastapi.endpoints.me import router
from api.infrastructure.fastapi.schemas.admin.keys import KeyResponse, KeysResponse
from api.use_cases.admin.keys import GetKeysCommand, GetKeysUseCase, GetKeysUseCaseSuccess
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.get(
    path=EndpointRoute.ME_KEYS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_keys(
    offset: int = Query(default=0, ge=0, description="Number of keys to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of keys to return."),
    sort_by: SortField = Query(default=SortField.ID, description="Field to sort by."),
    sort_order: SortOrder = Query(default=SortOrder.ASC, description="Sort order."),
    get_keys_use_case: GetKeysUseCase = Depends(get_keys_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> KeysResponse:
    """
    Get all your keys.
    """

    command = GetKeysCommand(
        user_id=request_context.get().user.id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    try:
        result = await get_keys_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_keys use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "offset": command.offset,
                "limit": command.limit,
                "sort_by": command.sort_by,
                "sort_order": command.sort_order,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetKeysUseCaseSuccess(key_page=key_page):
            return KeysResponse(
                total=key_page.total,
                offset=offset,
                limit=limit,
                data=[KeyResponse.model_validate(key, from_attributes=True) for key in key_page.data],
            )
