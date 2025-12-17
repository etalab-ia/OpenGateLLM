import datetime as dt
from http import HTTPMethod
from typing import Optional

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

from api.schemas.admin.providers import ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.roles import LimitType, PermissionType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.collections import CollectionVisibility
from api.schemas.core.metrics import Metric
from api.schemas.models import ModelType
from api.utils.variables import DEFAULT_TIMEOUT

Base = declarative_base()


class Usage(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())

    # foreign keys
    user_id: Mapped[int | None] = mapped_column(ForeignKey(column="user.id", ondelete="SET NULL"), index=True)
    token_id: Mapped[int | None] = mapped_column(ForeignKey(column="token.id", ondelete="SET NULL"), index=True)
    router_id: Mapped[int | None] = mapped_column(ForeignKey(column="router.id", ondelete="SET NULL"), index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey(column="provider.id", ondelete="SET NULL"), index=True)

    # identifiers (useful for historical analysis when foreign keys are deleted)
    user_email: Mapped[str | None]
    token_name: Mapped[str | None]
    router_name: Mapped[str | None]
    provider_model_name: Mapped[str | None]

    # request
    endpoint: Mapped[str]
    method: Mapped[HTTPMethod | None]

    # metrics
    latency: Mapped[int | None]
    ttft: Mapped[int | None]

    # response
    status: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[float | None]
    total_tokens: Mapped[int | None]
    cost: Mapped[float | None]
    kwh_min: Mapped[float | None]
    kwh_max: Mapped[float | None]
    kgco2eq_min: Mapped[float | None]
    kgco2eq_max: Mapped[float | None]

    user: Mapped["User"] = relationship(back_populates="usage")
    token: Mapped[Optional["Token"]] = relationship(back_populates="usage")
    router: Mapped[Optional["Router"]] = relationship(back_populates="usage")
    provider: Mapped[Optional["Provider"]] = relationship(back_populates="usage")


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())

    user: Mapped[list["User"]] = relationship(back_populates="role", passive_deletes=True)
    limits: Mapped[list["Limit"]] = relationship(back_populates="role", cascade="all, delete-orphan", passive_deletes=True)
    permissions: Mapped[list["Permission"]] = relationship(back_populates="role", cascade="all, delete-orphan", passive_deletes=True)


class Permission(Base):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(column="role.id", ondelete="CASCADE"))
    permission: Mapped[PermissionType]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())

    role: Mapped["Role"] = relationship(back_populates="permissions")

    __table_args__ = (UniqueConstraint("role_id", "permission", name="unique_permission_per_role"),)


class Limit(Base):
    __tablename__ = "limit"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey(column="role.id", ondelete="CASCADE"))
    router_id: Mapped[int] = mapped_column(ForeignKey(column="router.id", ondelete="CASCADE"))
    type: Mapped[LimitType]
    value: Mapped[int | None]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())

    role: Mapped["Role"] = relationship(back_populates="limits")
    router: Mapped["Router"] = relationship(back_populates="limit")

    __table_args__ = (UniqueConstraint("role_id", "router_id", "type", name="unique_rate_limit_per_role"),)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(index=True, unique=True)
    password: Mapped[str | None]
    name: Mapped[str | None]
    sub: Mapped[str | None]
    iss: Mapped[str | None]
    role_id: Mapped[int] = mapped_column(ForeignKey(column="role.id", ondelete="RESTRICT"))
    organization_id: Mapped[int | None] = mapped_column(ForeignKey(column="organization.id", ondelete="RESTRICT"))
    budget: Mapped[float | None]
    expires: Mapped[dt.datetime | None]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())
    priority: Mapped[int] = mapped_column(default=0)  # User priority: higher value means higher priority for rate limiting / scheduling (0 = default)

    usage: Mapped[list["Usage"]] = relationship(back_populates="user", passive_deletes=True)
    token: Mapped[list["Token"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    collection: Mapped[list["Collection"]] = relationship(back_populates="user", passive_deletes=True)
    role: Mapped["Role"] = relationship(back_populates="user", passive_deletes=True)
    organization: Mapped["Organization"] = relationship(back_populates="user", passive_deletes=True)
    router: Mapped[list["Router"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    provider: Mapped[list["Provider"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("sub", "iss", name="unique_user_email_sub_iss"),
        UniqueConstraint("id", "organization_id", name="unique_user_id_organization_id"),
    )


class Token(Base):
    __tablename__ = "token"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(column="user.id", ondelete="CASCADE"))
    name: Mapped[str | None]
    token: Mapped[str | None]
    expires: Mapped[dt.datetime | None]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())

    user: Mapped["User"] = relationship(back_populates="token")
    usage: Mapped[list["Usage"]] = relationship(back_populates="token", passive_deletes=True)


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True)
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="organization", passive_deletes=True)


class Collection(Base):
    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(column="user.id", ondelete="CASCADE"))
    name: Mapped[str]
    description: Mapped[str | None]
    visibility: Mapped[CollectionVisibility]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="collection")
    document: Mapped[list["Document"]] = relationship(back_populates="collection", cascade="all, delete-orphan", passive_deletes=True)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey(column="collection.id", ondelete="CASCADE"))
    name: Mapped[str]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())

    collection: Mapped["Collection"] = relationship(back_populates="document", passive_deletes=True)


class Router(Base):
    __tablename__ = "router"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey(column="user.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(unique=True)
    type: Mapped[ModelType]
    load_balancing_strategy: Mapped[RouterLoadBalancingStrategy]
    cost_prompt_tokens: Mapped[float] = mapped_column(default=0.0)
    cost_completion_tokens: Mapped[float] = mapped_column(default=0.0)
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="router")
    alias: Mapped[list["RouterAlias"]] = relationship(back_populates="router", cascade="all, delete-orphan", passive_deletes=True)
    provider: Mapped[list["Provider"]] = relationship(back_populates="router", cascade="all, delete-orphan", passive_deletes=True)
    limit: Mapped[list["Limit"]] = relationship(back_populates="router", cascade="all, delete-orphan", passive_deletes=True)
    usage: Mapped[list["Usage"]] = relationship(back_populates="router", passive_deletes=True)


class RouterAlias(Base):
    __tablename__ = "router_alias"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    router_id: Mapped[int] = mapped_column(ForeignKey(column="router.id", ondelete="CASCADE"))
    value: Mapped[str] = mapped_column(unique=True)

    router: Mapped["Router"] = relationship(back_populates="alias")


class Provider(Base):
    __tablename__ = "provider"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    router_id: Mapped[int] = mapped_column(ForeignKey(column="router.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey(column="user.id", ondelete="CASCADE"))
    type: Mapped[ProviderType]
    url: Mapped[str]
    key: Mapped[str | None]
    timeout: Mapped[int] = mapped_column(default=DEFAULT_TIMEOUT)
    model_name: Mapped[str]
    model_carbon_footprint_zone: Mapped[ProviderCarbonFootprintZone | None]
    model_carbon_footprint_total_params: Mapped[int] = mapped_column(default=0)
    model_carbon_footprint_active_params: Mapped[int] = mapped_column(default=0)
    qos_metric: Mapped[Metric | None]
    qos_limit: Mapped[float | None]
    max_context_length: Mapped[int | None]
    vector_size: Mapped[int | None]
    created: Mapped[dt.datetime] = mapped_column(insert_default=func.now())
    updated: Mapped[dt.datetime] = mapped_column(insert_default=func.now(), onupdate=func.now())

    router: Mapped["Router"] = relationship(back_populates="provider")
    user: Mapped["User"] = relationship(back_populates="provider")
    usage: Mapped[list["Usage"]] = relationship(back_populates="provider", passive_deletes=True)

    __table_args__ = (UniqueConstraint("router_id", "url", "model_name", name="unique_provider_router_id_url_model_name"),)
