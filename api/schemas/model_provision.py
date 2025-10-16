from typing import Any

from pydantic import Field

from api.schemas import BaseModel
from api.schemas.core.configuration import Model as ModelRouterSchema
from api.schemas.core.configuration import ModelProvider as ModelClientSchema
from api.schemas.core.configuration import RoutingStrategy
from api.schemas.models import ModelType

URL_PATTERN = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"


class AddModelRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the ModelRouter to add the ModelClient to.")
    model: ModelClientSchema = Field(description="Model to add.")

    # Optional fields
    model_type: ModelType | None = Field(default=None, description="Model type. Required when creating a new ModelRouter.")
    aliases: list[str] | None = Field(default=[], description="Aliases, to add for existing router, to set for new instance.")
    load_balancing_strategy: RoutingStrategy | None = Field(
        default=RoutingStrategy.ROUND_ROBIN, description="Routing Strategy when creating a new router."
    )
    owner: str | None = Field(default=None, description="ModelRouter owner when creating a new one.")

    additional_field: dict[str, Any] | None = Field(default=None, description="Additional or specific data")


class DeleteModelRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the ModelRouter to delete the ModelClient from.")
    url: str = Field(pattern=URL_PATTERN, description="URL of the model API.")
    model_name: str = Field(min_length=1, description="Name of the model to delete.")


class AddAliasesRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: list[str] = Field(default=[], description="Aliases to add.")


class DeleteAliasesRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: list[str] = Field(default=[], description="Aliases to delete.")


class RoutersResponse(BaseModel):
    routers: list[ModelRouterSchema] = Field(description="Currently existing ModelRouters.")
