import logging

from fastapi import APIRouter, Body, Depends, Path, Query, Security

from api.dependencies import create_me_key_use_case_factory, get_keys_use_case_factory, get_one_key_use_case_factory
from api.domain import SortField, SortOrder
from api.domain.key.errors import KeyAlreadyExistsError, KeyExpirationInvalidError, KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    KeyAlreadyExistsHTTPException,
    KeyExpirationInvalidHTTPException,
    KeyNotFoundHTTPException,
    UserNotFoundHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.keys import KeyResponse, KeysResponse
from api.infrastructure.fastapi.schemas.keys import CreateKeyBody
from api.use_cases.admin.keys import (
    CreateKeyCommand,
    CreateKeyUseCase,
    CreateKeyUseCaseSuccess,
    GetKeysCommand,
    GetKeysUseCase,
    GetKeysUseCaseSuccess,
    GetOneKeyCommand,
    GetOneKeyUseCase,
    GetOneKeyUseCaseSuccess,
)
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.KEYS.title()])


@router.post(
    path="/me/keys",
    dependencies=[Security(dependency=AccessController())],
    status_code=201,
    responses=get_documentation_responses([KeyAlreadyExistsHTTPException, KeyExpirationInvalidHTTPException, UserNotFoundHTTPException]),
    deprecated=True,
)
@router.post(
    path=EndpointRoute.KEYS,
    dependencies=[Security(dependency=AccessController())],
    status_code=201,
    responses=get_documentation_responses([KeyAlreadyExistsHTTPException, KeyExpirationInvalidHTTPException, UserNotFoundHTTPException]),
)
async def create_key(
    body: CreateKeyBody = Body(description="The key creation request."),
    create_me_key_use_case: CreateKeyUseCase = Depends(create_me_key_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> KeyResponse:
    """
    Create a new API key for the authenticated user.
    """

    command = CreateKeyCommand(user_id=authenticated_user.id, name=body.name, expire=body.expires)
    try:
        result = await create_me_key_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing create_me_key use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "name": body.name,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateKeyUseCaseSuccess(key=key):
            return KeyResponse.model_validate(key, from_attributes=True)
        case KeyAlreadyExistsError(name=name):
            raise KeyAlreadyExistsHTTPException(name)
        case KeyExpirationInvalidError(max_expiration_days=max_expiration_days):
            raise KeyExpirationInvalidHTTPException(max_expiration_days)
        case UserNotFoundError(id=user_id):
            raise UserNotFoundHTTPException(user_id)


@router.get(
    path="/me/keys",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
    deprecated=True,
)
@router.get(
    path=EndpointRoute.KEYS,
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
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> KeysResponse:
    """
    Get all your keys.
    """

    command = GetKeysCommand(
        user_id=authenticated_user.id,
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
                "authenticated_user_id": authenticated_user.id,
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


@router.get(
    path="/me/keys/{key_id}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([KeyNotFoundHTTPException]),
    deprecated=True,
)
@router.get(
    path=EndpointRoute.KEYS + "/{key_id}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([KeyNotFoundHTTPException]),
)
async def get_key(
    key_id: int = Path(description="The ID of the key to get."),
    get_one_key_use_case: GetOneKeyUseCase = Depends(get_one_key_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> KeyResponse:
    """
    Get one of your API keys by ID.
    """

    command = GetOneKeyCommand(key_id=key_id, user_id=authenticated_user.id)
    try:
        result = await get_one_key_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_key use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "key_id": key_id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetOneKeyUseCaseSuccess(key=key):
            return KeyResponse.model_validate(key, from_attributes=True)
        case KeyNotFoundError(id=not_found_key_id):
            raise KeyNotFoundHTTPException(not_found_key_id)
