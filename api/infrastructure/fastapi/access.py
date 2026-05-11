import time
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.dependencies import get_key_repository, get_request_context, get_secret_key
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.infrastructure.fastapi.endpoints.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException
from api.schemas.core.context import RequestContext

http_bearer = HTTPBearer()


async def get_current_key(
    request: Request,
    api_key: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    key_repository: KeyRepository = Depends(get_key_repository),
    secret_key: str = Depends(get_secret_key),
    request_context: RequestContext = Depends(get_request_context),
) -> None:
    if api_key.scheme != "Bearer":
        raise InvalidAuthenticationSchemeException()

    if not api_key.credentials:
        raise InvalidAPIKeyException()

    decoded_key = Key(value=api_key.credentials).decode(secret_key=secret_key)
    result = await key_repository.get_key_expiration(user_id=decoded_key.user_id, key_id=decoded_key.key_id)

    match result:
        case KeyNotFoundError():
            raise InvalidAPIKeyException()
        case int():
            if result is not None and result < time.time():
                raise InvalidAPIKeyException()

    request_context.get().user_id = decoded_key.user_id
    request_context.get().key_id = decoded_key.key_id
