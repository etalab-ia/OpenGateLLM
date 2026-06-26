import logging

from fastapi import Body, Depends, Security

from api.dependencies import get_sso_policy_use_case_factory, update_sso_policy_use_case_factory
from api.domain.auth.entities import NewSsoPolicy
from api.domain.auth.errors import SsoPolicyRuleAlreadyExistsError
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.infrastructure.fastapi import AccessController
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.admin import router
from api.infrastructure.fastapi.endpoints.exceptions import (
    InternalServerHTTPException,
    NotAdminUserHTTPException,
    OrganizationNotFoundHTTPException,
    RoleNotFoundHTTPException,
    SsoPolicyRuleAlreadyExistsHTTPException,
)
from api.infrastructure.fastapi.schemas.admin.sso import SsoPolicyResponse, SsoPolicyRulesBody
from api.use_cases.admin.sso import (
    GetSsoPolicyUseCase,
    GetSsoPolicyUseCaseSuccess,
    UpdateSsoPolicyCommand,
    UpdateSsoPolicyUseCase,
    UpdateSsoPolicyUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@router.get(
    path=EndpointRoute.ADMIN_SSO_POLICY,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    response_model=SsoPolicyResponse,
    responses=get_documentation_responses([NotAdminUserHTTPException]),
)
async def get_sso_policy(get_sso_policy_use_case: GetSsoPolicyUseCase = Depends(get_sso_policy_use_case_factory)) -> SsoPolicyResponse:
    """
    Gets the SSO policy.
    """
    try:
        result = await get_sso_policy_use_case.execute()
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_sso_policy use case",
            extra={"error_type": type(e).__name__},
        )
        raise InternalServerHTTPException()

    match result:
        case GetSsoPolicyUseCaseSuccess(policy=policy):
            return SsoPolicyResponse.model_validate(policy, from_attributes=True)


@router.put(
    path=EndpointRoute.ADMIN_SSO_POLICY,
    dependencies=[Security(dependency=AccessController(only_admin=True))],
    status_code=200,
    response_model=SsoPolicyResponse,
    responses=get_documentation_responses(
        [
            NotAdminUserHTTPException,
            RoleNotFoundHTTPException,
            SsoPolicyRuleAlreadyExistsHTTPException,
            OrganizationNotFoundHTTPException,
        ],
    ),
)
async def replace_sso_policy(
    body: SsoPolicyRulesBody = Body(description="The SSO policy rules to store."),
    update_sso_policy_use_case: UpdateSsoPolicyUseCase = Depends(update_sso_policy_use_case_factory),
) -> SsoPolicyResponse:
    """
    Replaces the SSO policy with the provided body, or creates a new policy if one does not exist.
    """
    command = UpdateSsoPolicyCommand(policy=NewSsoPolicy.model_validate(body.model_dump()))
    try:
        result = await update_sso_policy_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing update_sso_policy use case",
            extra={"error_type": type(e).__name__},
        )
        raise InternalServerHTTPException()

    match result:
        case UpdateSsoPolicyUseCaseSuccess(policy=policy):
            return SsoPolicyResponse.model_validate(policy, from_attributes=True)
        case SsoPolicyRuleAlreadyExistsError():
            raise SsoPolicyRuleAlreadyExistsHTTPException()
        case RoleNotFoundError():
            raise RoleNotFoundHTTPException()
        case OrganizationNotFoundError():
            raise OrganizationNotFoundHTTPException()
