from typing import Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.admin.organizations import (
    Organization,
    OrganizationRequest,
    Organizations,
    OrganizationsResponse,
    OrganizationUpdateRequest,
)
from api.schemas.admin.roles import PermissionType
from api.utils.context import global_context
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.ADMIN.title()])


@router.post(
    path=EndpointRoute.ADMIN_ORGANIZATIONS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=201,
    response_model=OrganizationsResponse,
)
async def create_organization(
    request: Request,
    body: OrganizationRequest = Body(description="The organization creation request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    organization_id = await global_context.identity_access_manager.create_organization(postgres_session=postgres_session, name=body.name)
    return JSONResponse(status_code=201, content={"id": organization_id})


@router.delete(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def delete_organization(
    request: Request,
    organization: int = Path(description="The ID of the organization to delete."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    await global_context.identity_access_manager.delete_organization(postgres_session=postgres_session, organization_id=organization)
    return Response(status_code=204)


@router.patch(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=204,
)
async def update_organization(
    request: Request,
    organization: int = Path(description="The ID of the organization to update."),
    body: OrganizationUpdateRequest = Body(description="The organization update request."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    await global_context.identity_access_manager.update_organization(postgres_session=postgres_session, organization_id=organization, name=body.name)
    return Response(status_code=204)


@router.get(
    path=EndpointRoute.ADMIN_ORGANIZATIONS + "/{organization:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Organization,
)
async def get_organization(
    request: Request,
    organization: int = Path(description="The ID of the organization to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    organizations = await global_context.identity_access_manager.get_organizations(postgres_session=postgres_session, organization_id=organization)
    return JSONResponse(content=organizations[0].model_dump(), status_code=200)


@router.get(
    path=EndpointRoute.ADMIN_ORGANIZATIONS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.ADMIN]))],
    status_code=200,
    response_model=Organizations,
)
async def get_organizations(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the organizations to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the organizations to get."),
    order_by: Literal["id", "name", "created", "updated"] = Query(default="id", description="The field to order the organizations by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the organizations by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    data = await global_context.identity_access_manager.get_organizations(
        postgres_session=postgres_session,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )
    return JSONResponse(content=Organizations(data=data).model_dump(), status_code=200)
