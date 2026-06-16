from contextvars import ContextVar
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from api.dependencies import _key_repository, _user_with_role_query, get_request_context, get_secret_key
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user import UserWithRoleQuery
from api.infrastructure.fastapi.endpoints.exceptions import (
    AccountExpiredHTTPException,
    InvalidAPIKeyHTTPException,
    InvalidAuthenticationSchemeHTTPException,
    NotAdminUserHTTPException,
)
from api.schemas.core.context import RequestContext

TOKEN_PREFIX = "sk-"
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
        secret_key: str = Depends(get_secret_key),
        key_repository: KeyRepository = Depends(_key_repository),
        user_with_role_query: UserWithRoleQuery = Depends(_user_with_role_query),
        request_context: ContextVar[RequestContext] = Depends(get_request_context),
    ) -> None:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeHTTPException()

        if not api_key.credentials:
            raise InvalidAPIKeyHTTPException()

        if not api_key.credentials.startswith(TOKEN_PREFIX):
            raise InvalidAPIKeyHTTPException()

        try:
            jwt_token = api_key.credentials.split(TOKEN_PREFIX)[1]
            claims = jwt.decode(token=jwt_token, key=secret_key, algorithms=["HS256"])
            decoded_key = Key.build_from_claims(claims=claims)

        except (JWTError, IndexError, KeyError, ValueError):
            raise InvalidAPIKeyHTTPException()

        self._set_value_in_request_context(request_context=request_context, key="key", value=decoded_key)

        result = await key_repository.get_key_by_id(key_id=decoded_key.id)
        match result:
            case KeyNotFoundError():
                raise InvalidAPIKeyHTTPException()
            case Key() as key:
                if not decoded_key.is_valid(expected_key=key):
                    raise InvalidAPIKeyHTTPException()

        user = await user_with_role_query.get_user_with_role_by_id(user_id=key.user_id)

        if user.has_expired:
            raise AccountExpiredHTTPException()

        if self.only_admin and not user.is_admin:
            raise NotAdminUserHTTPException()

        self._set_value_in_request_context(request_context=request_context, key="user", value=user)
