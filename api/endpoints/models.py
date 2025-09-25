import traceback
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelClient
from api.helpers._accesscontroller import AccessController
from api.schemas.model_provision import AddAliasesRequest, AddModelRequest, DeleteAliasesRequest, DeleteModelRequest, RoutersResponse
from api.schemas.models import Model, Models
from api.sql.session import get_db_session
from api.utils.context import global_context
from api.utils.variables import (
    DEFAULT_APP_NAME,
    ENDPOINT__MODELS,
    ENDPOINT__MODELS_ALIAS,
    ENDPOINT__ROUTERS,
    ROUTER__MODELS,
)

router = APIRouter(prefix="/v1", tags=[ROUTER__MODELS.title()])


@router.get(path=ENDPOINT__MODELS + "/{model:path}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Model)
async def get_model(request: Request, model: str = Path(description="The name of the model to get.")) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """

    models = await global_context.model_registry.list(model=model)
    if not models:
        raise HTTPException(status_code=404, detail=f"Model '{model}' not found")

    model = models[0]

    return JSONResponse(content=model.model_dump(), status_code=200)


@router.get(path=ENDPOINT__MODELS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Models)
async def get_models(request: Request) -> JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """

    data = await global_context.model_registry.list()

    return JSONResponse(content=Models(data=data).model_dump(), status_code=200)


@router.post(path=ENDPOINT__MODELS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_model(request: Request, body: AddModelRequest, session: AsyncSession = Depends(get_db_session)) -> Response:
    """
    Adds a new provider. NB: the config's routers and providers are read-only, and cannot be altered.
    """

    if body.owner == DEFAULT_APP_NAME:
        raise HTTPException(status_code=401, detail="Owner cannot be the API itself")

    client_kwargs = body.additional_field if body.additional_field is not None else {}

    client = BaseModelClient.from_schema(body.model, **client_kwargs)

    try:
        await global_context.model_registry.add_client(
            router_name=body.router_name,
            model_client=client,
            session=session,
            model_type=body.model_type,
            aliases=body.aliases,
            routing_strategy=body.routing_strategy,
            owner=body.owner,
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.print_exception(e))

    return Response(status_code=201)


@router.delete(path=ENDPOINT__MODELS, dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_model(request: Request, body: DeleteModelRequest, session: AsyncSession = Depends(get_db_session)) -> Response:
    """
    Removes a provider. NB: the config's routers and providers are read-only, and cannot be altered.
    """
    try:
        await global_context.model_registry.delete_client(
            router_name=body.router_name,
            api_url=body.url,
            model_name=body.model_name,
            session=session,
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=204)


@router.post(path=ENDPOINT__MODELS_ALIAS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_alias(request: Request, body: AddAliasesRequest, session: AsyncSession = Depends(get_db_session)) -> Response:
    """
    Adds an alias to a router. NB: the config's routers and providers are read-only, and cannot be altered.
    """
    try:
        await global_context.model_registry.add_aliases(
            router_name=body.router_name,
            aliases=body.aliases,
            session=session,
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=201)


@router.delete(path=ENDPOINT__MODELS_ALIAS, dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_alias(
    request: Request,
    body: DeleteAliasesRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Removes an alias from a router. NB: the config's routers and providers are read-only, and cannot be altered.
    """
    try:
        await global_context.model_registry.delete_aliases(
            router_name=body.router_name,
            aliases=body.aliases,
            session=session,
        )
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=204)


@router.get(path=ENDPOINT__ROUTERS, status_code=200, dependencies=[Security(dependency=AccessController())], response_model=RoutersResponse)
async def get_routers(request: Request) -> JSONResponse:
    """
    Gives all the existing routers, with their clients.
    Sensitive information, such as providers' URL and API keys, are censored.
    """
    # We get client & router "quickly" (before processing data) to avoid
    # weird data and inconsistency due to concurrence.
    routers = await global_context.model_registry.get_router_instances()
    clients = [await r.get_clients() for r in routers]

    router_schemas = []

    for i, r in enumerate(routers):
        if len(clients[i]) == 0:
            # No clients, ModelRouter is about to get deleted
            continue

        router_schemas.append((await r.as_schema()))

    return JSONResponse(content=RoutersResponse(routers=router_schemas).model_dump(), status_code=200)
