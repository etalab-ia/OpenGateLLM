from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.dependencies import get_key_repository, get_master_key, get_request_context
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.schemas.core.context import RequestContext
from api.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException

http_bearer = HTTPBearer()


async def get_current_key(
    request: Request,
    api_key: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    key_repository: KeyRepository = Depends(get_key_repository),  # factory vers PostgresKeyValidator
    master_key: str = Depends(get_master_key),
    request_context: RequestContext = Depends(get_request_context),
) -> Key:
    if api_key.scheme != "Bearer":
        raise InvalidAuthenticationSchemeException()

    if not api_key.credentials:
        raise InvalidAPIKeyException()

    decoded_key = Key(value=api_key.credentials).decode(master_key=master_key)
    await key_repository.check_key_exists(user_id=decoded_key.user_id, key_id=decoded_key.key_id)

    request_context.get().user_id = decoded_key.user_id
    request_context.get().key_id = decoded_key.key_id
