import logging
import time
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.admin.roles import PermissionType
from api.schemas.admin.users import User
from api.schemas.me.info import UserInfo
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException
from api.utils.variables import (
    ENDPOINT__ME_INFO,
)

logger = logging.getLogger(__name__)


class AccessRepository:
    """
    Access controller ensure user access:
    - API key validation
    - rate limiting application (per requests and per tokens)
    - permissions to access the requested resource

    Access controller is used as a dependency of all endpoints.
    """

    async def __call__(
        self,
        request: Request,
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
        postgres_session: AsyncSession = Depends(get_postgres_session),
    ) -> User:
        user_info, key_id, key_name = await self._check_api_key(request=request, api_key=api_key, postgres_session=postgres_session)
        await self._check_permissions(permissions=user_info.permissions)
        body = await self._safely_parse_body(request)

        # add authenticated user to request state for logging usages
        context = request_context.get()
        context.user_info = user_info
        context.key_id = key_id
        context.key_name = key_name

        return user_info

    async def _check_api_key(self, request: Request, api_key: HTTPAuthorizationCredentials, postgres_session: AsyncSession) -> tuple[UserInfo, int]:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        # master user can do anything
        if api_key.credentials == global_context.identity_access_manager.master_key:
            user_info = UserInfo(
                id=0,
                email="master",
                name="master",
                budget=None,
                limits=[],
                permissions=[permission for permission in PermissionType],
                expires=None,
                created=0,
                updated=0,
                organization_id=0,
                priority=0,
            )
            key_id = 0
            key_name = "master"
        else:
            user_id, key_id, key_name = await global_context.identity_access_manager.check_token(
                postgres_session=postgres_session, token=api_key.credentials
            )
            if not user_id:
                raise InvalidAPIKeyException()

            user_info = await global_context.identity_access_manager.get_user_info(postgres_session=postgres_session, user_id=user_id)

            # invalid token if user is expired, except for /me and /me/role endpoints
            if user_info.expires and user_info.expires < time.time() and not request.url.path.endswith(ENDPOINT__ME_INFO):
                raise InvalidAPIKeyException()

        return user_info, key_id, key_name
