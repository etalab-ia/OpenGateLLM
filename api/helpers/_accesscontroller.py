import json
import logging
import time
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.admin.roles import Limit, LimitType, PermissionType, Role
from api.schemas.admin.users import User
from api.schemas.collections import CollectionVisibility
from api.schemas.me import UserInfo
from api.sql.session import get_db_session
from api.utils.context import global_context, request_context
from api.utils.exceptions import (
    InsufficientBudgetException,
    InsufficientPermissionException,
    InvalidAPIKeyException,
    InvalidAuthenticationSchemeException,
    RateLimitExceeded,
)
from api.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__COLLECTIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__FILES,
    ENDPOINT__ME_INFO,
    ENDPOINT__MODELS,
    ENDPOINT__MODELS_ALIAS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
    ENDPOINT__ROUTERS,
    ENDPOINT__SEARCH,
)

logger = logging.getLogger(__name__)


class _UserModelLimits(BaseModel):
    """
    PyDantic model to store user limits for each model in AccessController helper.
    """

    tpm: int = 0
    tpd: int = 0
    rpm: int = 0
    rpd: int = 0


class AccessController:
    """
    Access controller ensure user access:
    - API key validation
    - rate limiting application (per requests and per tokens)
    - permissions to access the requested resource

    Access controller is used as a dependency of all endpoints.
    """

    def __init__(self, permissions: List[PermissionType] = None):
        self.permissions = permissions if permissions is not None else []

    async def __call__(
        self,
        request: Request,
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
        session: AsyncSession = Depends(get_db_session)
    ) -> User:  # fmt: off
        user_info, limits, token_id = await self._check_api_key(api_key=api_key, session=session)

        # invalid token if user is expired, except for /me and /me/role endpoints
        if user_info.expires_at and user_info.expires_at < time.time() and not request.url.path.endswith(ENDPOINT__ME_INFO):
            raise InvalidAPIKeyException()

        await self._check_permissions(permissions=user_info.permissions)

        # add authenticated user to request state for logging usages
        context = request_context.get()
        context.user_info = user_info
        context.token_id = token_id

        if request.url.path.endswith(ENDPOINT__AUDIO_TRANSCRIPTIONS) and request.method in ["POST"]:
            await self._check_audio_transcription(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__CHAT_COMPLETIONS) and request.method in ["POST", "PATCH"]:
            await self._check_chat_completions(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__COLLECTIONS) and request.method in ["POST"]:
            await self._check_collections(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__EMBEDDINGS) and request.method in ["POST"]:
            await self._check_embeddings(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__FILES) and request.method in ["POST"]:
            await self._check_files(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__OCR) and request.method in ["POST"]:
            await self._check_ocr(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__RERANK) and request.method in ["POST"]:
            await self._check_rerank(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__SEARCH) and request.method in ["POST"]:
            await self._check_search(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__MODELS) and request.method in ["POST", "DELETE"]:
            await self._check_provider(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__MODELS_ALIAS) and request.method in ["POST", "DELETE"]:
            await self._check_provider(user_info=user_info, limits=limits, request=request)

        if request.url.path.endswith(ENDPOINT__ROUTERS) and request.method in ["GET"]:
            await self._check_provider(user_info=user_info, limits=limits, request=request)

        return user_info

    def __get_user_limits(self, user_info: UserInfo) -> Dict[str, _UserModelLimits]:
        limits = {}
        for model in global_context.model_registry.models:
            limits[model] = _UserModelLimits()
            for limit in user_info.limits:
                if limit.model == model and limit.type == LimitType.TPM:
                    limits[model].tpm = limit.value
                elif limit.model == model and limit.type == LimitType.TPD:
                    limits[model].tpd = limit.value
                elif limit.model == model and limit.type == LimitType.RPM:
                    limits[model].rpm = limit.value
                elif limit.model == model and limit.type == LimitType.RPD:
                    limits[model].rpd = limit.value

        # web search limits as pseudo model
        limits["web-search"] = _UserModelLimits()
        for limit in user_info.limits:
            if limit.model == "web-search" and limit.type == LimitType.RPM:
                limits["web-search"].rpm = limit.value
            elif limit.model == "web-search" and limit.type == LimitType.RPD:
                limits["web-search"].rpd = limit.value

        return limits

    async def _check_api_key(
        self, api_key: HTTPAuthorizationCredentials, session: AsyncSession
    ) -> tuple[User, Role, Dict[str, _UserModelLimits], int | None]:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        if api_key.credentials == global_context.identity_access_manager.master_key:  # master user can do anything
            limits = [Limit(model=model, type=type, value=None) for model in global_context.model_registry.models for type in LimitType]
            permissions = [permission for permission in PermissionType]

            master_info = UserInfo(
                id=0,
                email="master",
                name="master",
                budget=None,
                limits=limits,
                permissions=permissions,
                expires_at=None,
                created_at=0,
                updated_at=0,
                organization_id=0,
            )

            master_limits = self.__get_user_limits(user_info=master_info)

            return master_info, master_limits, None

        user_id, token_id = await global_context.identity_access_manager.check_token(session=session, token=api_key.credentials)
        if not user_id:
            raise InvalidAPIKeyException()

        user_info = await global_context.identity_access_manager.get_user_info(session=session, user_id=user_id)
        limits = self.__get_user_limits(user_info=user_info)

        return user_info, limits, token_id

    async def _check_permissions(self, permissions: List[PermissionType]) -> None:
        if self.permissions and not all(perm in permissions for perm in self.permissions):
            raise InsufficientPermissionException()

    async def _check_request_limits(self, request: Request, user_info: UserInfo, limits: Dict[str, _UserModelLimits], model: Optional[str] = None) -> None:  # fmt: off
        if not model:
            return

        model = global_context.model_registry.aliases.get(model, model)

        if model not in limits:  # unknown model (404 will be raised by the model client)
            return

        if limits[model].rpm == 0 or limits[model].rpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        check = await global_context.limiter.hit(user_id=user_info.id, model=model, type=LimitType.RPM, value=limits[model].rpm)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user_info.id, model=model, type=LimitType.RPM, value=limits[model].rpm)
            raise RateLimitExceeded(detail=f"{str(limits[model].rpm)} requests for {model} per minute exceeded (remaining: {remaining}).")

        check = await global_context.limiter.hit(user_id=user_info.id, model=model, type=LimitType.RPD, value=limits[model].rpd)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user_info.id, model=model, type=LimitType.RPD, value=limits[model].rpd)
            raise RateLimitExceeded(detail=f"{str(limits[model].rpd)} requests for {model} per day exceeded (remaining: {remaining}).")

    async def _check_token_limits(self, request: Request, user_info: UserInfo, limits: Dict[str, _UserModelLimits], prompt_tokens: int, model: Optional[str] = None) -> None:  # fmt: off
        if not model or not prompt_tokens:
            return

        model = global_context.model_registry.aliases.get(model, model)

        if model not in limits:  # unknown model (404 will be raised by the model client)
            return

        if limits[model].tpm == 0 or limits[model].tpd == 0:
            raise InsufficientPermissionException(detail=f"Insufficient permissions to access the model {model}.")

        # compute the cost (number of hits) of the request by the number of tokens
        check = await global_context.limiter.hit(user_id=user_info.id, model=model, type=LimitType.TPM, value=limits[model].tpm, cost=prompt_tokens)

        if not check:
            remaining = await global_context.limiter.remaining(user_id=user_info.id, model=model, type=LimitType.TPM, value=limits[model].tpm)
            raise RateLimitExceeded(detail=f"{str(limits[model].tpm)} input tokens for {model} per minute exceeded (remaining: {remaining}).")

        check = await global_context.limiter.hit(user_id=user_info.id, model=model, type=LimitType.TPD, value=limits[model].tpd, cost=prompt_tokens)
        if not check:
            remaining = await global_context.limiter.remaining(user_id=user_info.id, model=model, type=LimitType.TPD, value=limits[model].tpd)
            raise RateLimitExceeded(detail=f"{str(limits[model].tpd)} input tokens for {model} per day exceeded (remaining: {remaining}).")

    async def _check_budget(self, user_info: UserInfo, model: Optional[str] = None) -> None:
        if not model:
            return

        model = global_context.model_registry.aliases.get(model, model)

        if model not in global_context.model_registry.models:
            return

        model = await global_context.model_registry(model=model)
        if model.cost_prompt_tokens == 0 and model.cost_completion_tokens == 0:  # free model
            return

        if user_info.budget == 0:
            raise InsufficientBudgetException(detail="Insufficient budget.")

    async def _check_audio_transcription(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        form = await request.form()
        form = {key: value for key, value in form.items()} if form else {}

        await self._check_request_limits(request=request, user_info=user_info, limits=limits, model=form.get("model"))
        await self._check_budget(user_info=user_info, model=form.get("model"))

    async def _check_chat_completions(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        await self._check_request_limits(request=request, user_info=user_info, limits=limits, model=body.get("model"))

        if body.get("search", False):  # count the search request as one request to the search model (embeddings)
            await self._check_request_limits(
                request=request, user_info=user_info, limits=limits, model=global_context.document_manager.vector_store_model.name
            )
            if body.get("search_args", {}).get("web_search", False):
                await self._check_request_limits(request=request, user_info=user_info, limits=limits, model="web-search")

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__CHAT_COMPLETIONS, body=body)
        await self._check_token_limits(request=request, user_info=user_info, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user_info=user_info, model=body.get("model"))

    async def _check_collections(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        if body.get("visibility") == CollectionVisibility.PUBLIC and PermissionType.CREATE_PUBLIC_COLLECTION not in user_info.permissions:
            raise InsufficientPermissionException("Missing permission to update collection visibility to public.")

    async def _check_embeddings(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        await self._check_request_limits(request=request, user_info=user_info, limits=limits, model=body.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__EMBEDDINGS, body=body)
        await self._check_token_limits(request=request, user_info=user_info, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user_info=user_info, model=body.get("model"))

    async def _check_files(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        await self._check_request_limits(
            request=request, user_info=user_info, limits=limits, model=global_context.document_manager.vector_store_model.name
        )

        await self._check_budget(user_info=user_info, model=global_context.document_manager.vector_store_model.name)

    async def _check_ocr(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        form = await request.form()
        form = {key: value for key, value in form.items()} if form else {}

        await self._check_request_limits(request=request, user_info=user_info, limits=limits, model=form.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__OCR, body=form)
        await self._check_token_limits(request=request, user_info=user_info, limits=limits, prompt_tokens=prompt_tokens, model=form.get("model"))

        await self._check_budget(user_info=user_info, model=form.get("model"))

    async def _check_rerank(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        await self._check_request_limits(request=request, user_info=user_info, limits=limits, model=body.get("model"))

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__RERANK, body=body)
        await self._check_token_limits(request=request, user_info=user_info, limits=limits, prompt_tokens=prompt_tokens, model=body.get("model"))

        await self._check_budget(user_info=user_info, model=body.get("model"))

    async def _check_search(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        # count the search request as one request to the search model (embeddings)
        await self._check_request_limits(
            request=request, user_info=user_info, limits=limits, model=global_context.document_manager.vector_store_model.name
        )

        if body.get("web_search", False):
            await self._check_request_limits(request=request, user_info=user_info, limits=limits, model="web-search")

        prompt_tokens = global_context.tokenizer.get_prompt_tokens(endpoint=ENDPOINT__SEARCH, body=body)
        await self._check_token_limits(
            request=request,
            user_info=user_info,
            limits=limits,
            prompt_tokens=prompt_tokens,
            model=global_context.document_manager.vector_store_model.name,
        )

        await self._check_budget(user_info=user_info, model=global_context.document_manager.vector_store_model.name)

    async def _check_tokens(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        # if the token is for another user, we don't check the expiration date
        if body.get("user") and PermissionType.CREATE_USER not in user_info.permissions:
            raise InsufficientPermissionException("Missing permission to create token for another user.")

    async def _check_provider(self, user_info: UserInfo, limits: Dict[str, _UserModelLimits], request: Request) -> None:
        body = await self._safely_parse_body(request)

        if body.get("user") and PermissionType.PROVIDE_MODELS not in user_info.permissions:
            raise InsufficientPermissionException("Missing permission to interact with provider's endpoints.")

    async def _safely_parse_body(self, request: Request) -> Dict:
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
