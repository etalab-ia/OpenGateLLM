import json
import logging
import time
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.role.entities import PermissionType
from api.helpers._identityaccessmanager import CheckTokenResult
from api.schemas.admin.users import User
from api.schemas.me.info import UserInfo
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.exceptions import InsufficientPermissionException, InvalidAPIKeyException, InvalidAuthenticationSchemeException
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


class AccessController:
    """
    Access controller ensure user access:
    - API key validation
    - rate limiting application (per requests and per tokens)
    - permissions to access the requested resource

    Access controller is used as a dependency of all endpoints.
    """

    def __init__(self, permissions: list[PermissionType] = None):
        self.permissions = permissions if permissions is not None else []

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

        if request.url.path.endswith(EndpointRoute.AUDIO_TRANSCRIPTIONS) and request.method in ["POST"]:
            await self._check_audio_transcription(body=body, user_info=user_info, postgres_session=postgres_session)

        if request.url.path.endswith(EndpointRoute.CHAT_COMPLETIONS) and request.method in ["POST", "PATCH"]:
            await self._check_chat_completions(body=body, user_info=user_info, postgres_session=postgres_session)

        if request.url.path.endswith(EndpointRoute.EMBEDDINGS) and request.method in ["POST"]:
            await self._check_embeddings(body=body, user_info=user_info, postgres_session=postgres_session)

        if request.url.path.endswith(EndpointRoute.OCR) and request.method in ["POST"]:
            await self._check_ocr(body=body, user_info=user_info, postgres_session=postgres_session)

        if request.url.path.endswith(EndpointRoute.RERANK) and request.method in ["POST"]:
            await self._check_rerank(body=body, user_info=user_info, postgres_session=postgres_session)

        return user_info

    @staticmethod
    async def _check_api_key(request: Request, api_key: HTTPAuthorizationCredentials, postgres_session: AsyncSession) -> tuple[UserInfo, int, str]:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        token_result: CheckTokenResult = await global_context.identity_access_manager.check_token(
            postgres_session=postgres_session, token=api_key.credentials
        )
        if token_result.user_id is None:
            raise InvalidAPIKeyException()

        user_info = await global_context.identity_access_manager.get_user_info(postgres_session=postgres_session, user_id=token_result.user_id)

        # invalid token if user is expired, except for /me and /me/role endpoints
        if user_info.expires and user_info.expires < time.time() and not request.url.path.endswith(EndpointRoute.ME_INFO):
            raise InvalidAPIKeyException()

        return user_info, token_result.token_id, token_result.token_name

    async def _check_permissions(self, permissions: list[PermissionType]) -> None:
        if PermissionType.ADMIN in permissions:
            return
        if self.permissions and not set(permissions).intersection(set(self.permissions)):
            raise InsufficientPermissionException()

    @staticmethod
    async def _check_audio_transcription(body: dict, user_info: UserInfo, postgres_session: AsyncSession) -> None:
        router_id = await global_context.model_registry.get_router_id_from_model_name(model_name=body.get("model"), postgres_session=postgres_session)
        if router_id is None:
            return
        await global_context.limiter.check_user_limits(user_info=user_info, router_id=router_id)

    @staticmethod
    async def _check_chat_completions(body: dict, user_info: UserInfo, postgres_session: AsyncSession) -> None:
        router_id = await global_context.model_registry.get_router_id_from_model_name(model_name=body.get("model"), postgres_session=postgres_session)
        if router_id is None:
            return

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=EndpointRoute.CHAT_COMPLETIONS, body=body)
        await global_context.limiter.check_user_limits(user_info=user_info, router_id=router_id, prompt_tokens=prompt_tokens)

    @staticmethod
    async def _check_embeddings(body: dict, user_info: UserInfo, postgres_session: AsyncSession) -> None:
        router_id = await global_context.model_registry.get_router_id_from_model_name(model_name=body.get("model"), postgres_session=postgres_session)
        if router_id is None:
            return
        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=EndpointRoute.EMBEDDINGS, body=body)
        await global_context.limiter.check_user_limits(user_info=user_info, router_id=router_id, prompt_tokens=prompt_tokens)

    @staticmethod
    async def _check_ocr(body: dict, user_info: UserInfo, postgres_session: AsyncSession) -> None:
        router_id = await global_context.model_registry.get_router_id_from_model_name(model_name=body.get("model"), postgres_session=postgres_session)
        if router_id is None:
            return
        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=EndpointRoute.OCR, body=body)
        await global_context.limiter.check_user_limits(user_info=user_info, router_id=router_id, prompt_tokens=prompt_tokens)

    @staticmethod
    async def _check_rerank(body: dict, user_info: UserInfo, postgres_session: AsyncSession) -> None:
        router_id = await global_context.model_registry.get_router_id_from_model_name(model_name=body.get("model"), postgres_session=postgres_session)
        if router_id is None:
            return
        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=EndpointRoute.RERANK, body=body)
        await global_context.limiter.check_user_limits(user_info=user_info, router_id=router_id, prompt_tokens=prompt_tokens)

    @staticmethod
    async def _safely_parse_body(request: Request) -> dict:
        """Safely parse request body as JSON or form data, handling encoding errors."""
        try:
            # Check content type to determine parsing strategy
            content_type = request.headers.get("content-type", "").lower()

            if content_type.startswith("multipart/form-data") or content_type.startswith("application/x-www-form-urlencoded"):
                # Handle multipart forms and URL-encoded forms
                try:
                    form_data = await request.form()
                    # Convert form data to dictionary, handling file uploads
                    result = {}
                    for key, value in form_data.items():
                        if hasattr(value, "filename"):  # File upload
                            # For file uploads, store filename and content type info
                            result[key] = {
                                "filename": value.filename,
                                "content_type": value.content_type,
                                "size": value.size if hasattr(value, "size") else None,
                            }
                        else:
                            # Regular form field
                            result[key] = value
                    return result
                except Exception:
                    logger.warning("Failed to parse multipart/form-data or application/x-www-form-urlencoded body.", exc_info=True)
                    return {}
            else:
                # Handle JSON content
                body = await request.body()
                if not body:
                    return {}

                # Try to decode as UTF-8 first
                try:
                    body_str = body.decode("utf-8")
                except UnicodeDecodeError:
                    # If UTF-8 fails, try with error handling to replace invalid characters
                    body_str = body.decode("utf-8", errors="replace")

                return json.loads(body_str)
        except (json.JSONDecodeError, AttributeError, ValueError):
            logger.warning("Failed to parse request body as JSON or form data.", exc_info=True)
            return {}
