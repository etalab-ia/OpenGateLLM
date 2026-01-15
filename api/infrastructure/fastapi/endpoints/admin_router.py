from fastapi import APIRouter, Body, Depends, Request, Security
from fastapi.responses import JSONResponse

from api.dependencies import create_router_use_case, get_request_context
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.schemas.routers import CreateRouter, CreateRouterResponse
from api.use_cases.admin import CreateRouterUseCase
from api.utils.variables import ENDPOINT__ADMIN_ROUTERS, ROUTER__ADMIN

router = APIRouter(prefix="/v1", tags=[ROUTER__ADMIN.title()])


@router.post(path=ENDPOINT__ADMIN_ROUTERS, dependencies=[Security(dependency=get_current_key)], status_code=201)
async def create_router(
    request: Request,
    body: CreateRouter = Body(description="The router creation request."),
    create_router_use_case: CreateRouterUseCase = Depends(create_router_use_case),
    request_context: RequestContext = Depends(get_request_context),
) -> JSONResponse:
    """
    Create a model (without any providers).
    """
    created_router = await create_router_use_case.execute(
        user_id=request_context.get().user_id,
        name=body.name,
        router_type=body.type,
        aliases=body.aliases,
        load_balancing_strategy=body.load_balancing_strategy,
        cost_prompt_tokens=body.cost_prompt_tokens,
        cost_completion_tokens=body.cost_completion_tokens,
    )
    return JSONResponse(
        status_code=201,
        content=CreateRouterResponse(
            id=created_router.id,
            name=created_router.name,
            type=created_router.type,
            aliases=created_router.aliases,
            load_balancing_strategy=created_router.load_balancing_strategy,
            cost_prompt_tokens=created_router.cost_prompt_tokens,
            cost_completion_tokens=created_router.cost_completion_tokens,
        ).model_dump(),
    )

    # created_router = await create_router_use_case.execute(
    #     user_id=request_context.get().user_id,
    #     name=body.name,
    #     type=body.type,
    #     aliases=body.aliases,
    #     load_balancing_strategy=body.load_balancing_strategy,
    #     cost_prompt_tokens=body.cost_prompt_tokens,
    #     cost_completion_tokens=body.cost_completion_tokens
    # )
    # return JSONResponse(
    #     status_code=201,
    #     content=CreateRouterResponse(
    #         id=created_router.id,
    #         name=created_router.name,
    #         type=created_router.type,
    #         aliases=created_router.aliases,
    #         load_balancing_strategy=created_router.load_balancing_strategy,
    #         cost_prompt_tokens=created_router.cost_prompt_tokens,
    #         cost_completion_tokens=created_router.cost_completion_tokens
    #     ).model_dump()
    # )
