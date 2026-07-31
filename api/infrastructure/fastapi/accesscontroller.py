from contextvars import ContextVar
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import ValidationError

from api.dependencies import _authenticated_user_query, _key_repository
from api.domain.key import KeyEncoder, KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user import AuthenticatedUserQuery
from api.infrastructure.fastapi._requestcontext import RequestContext
from api.infrastructure.fastapi.dependencies import get_request_context
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    InvalidAPIKeyHTTPException,
    InvalidAuthenticationSchemeHTTPException,
    NotAdminUserHTTPException,
)

http_bearer = HTTPBearer()


class AccessController:
    def __init__(self, only_admin: bool = False):
        self.only_admin = only_admin

    @staticmethod
    def _set_value_in_request_context(request_context: ContextVar[RequestContext], key: str, value: Any) -> None:
        setattr(request_context.get(), key, value)

    async def __call__(
        self,
        request: Request,
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
        key_repository: KeyRepository = Depends(_key_repository),
        authenticated_user_query: AuthenticatedUserQuery = Depends(_authenticated_user_query),
        request_context: ContextVar[RequestContext] = Depends(get_request_context),
    ) -> None:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeHTTPException()

        if not api_key.credentials:
            raise InvalidAPIKeyHTTPException()

        if not api_key.credentials.startswith(KeyEncoder.KEY_PREFIX):
            raise InvalidAPIKeyHTTPException()

        try:
            claims = key_repository.key_encoder.decode(key_value=api_key.credentials)
            decoded_key = Key.build_from_claims(claims=claims)
        except (JWTError, KeyError, ValidationError):
            raise InvalidAPIKeyHTTPException()

        self._set_value_in_request_context(request_context=request_context, key="key", value=decoded_key)

        result = await key_repository.get_key_by_id(key_id=decoded_key.id)
        match result:
            case KeyNotFoundError():
                raise InvalidAPIKeyHTTPException()
            case Key() as key:
                if not decoded_key.is_valid(expected_key=key):
                    raise InvalidAPIKeyHTTPException()

        user = await authenticated_user_query.get_user_by_id(user_id=key.user_id)

        if user.has_expired:
            raise AccountExpiredHTTPException()

        if self.only_admin and not user.is_admin:
            raise NotAdminUserHTTPException()

        self._set_value_in_request_context(request_context=request_context, key="user", value=user)
