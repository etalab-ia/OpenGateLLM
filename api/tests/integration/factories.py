from datetime import datetime, timedelta
import random
import unicodedata

import factory
from factory import fuzzy
from factory.alchemy import SQLAlchemyModelFactory

from api.domain.role.entities import LimitType, PermissionType
from api.domain.userinfo.entities import UserInfo
from api.schemas.admin.providers import ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.schemas.models import ModelType
from api.sql.models import Limit, Organization, Provider, Role, Router, RouterAlias, Token, User


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"


class OrganizationFactory(BaseFactory):
    """Factory pour créer des organisations de test."""

    class Meta:
        model = Organization

    name = factory.Faker("company", locale="fr_FR")
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        administration = factory.Trait(name=factory.Faker("bothify", text="Administration ####"))
        ministere = factory.Trait(name=factory.Faker("bothify", text="Ministere ####"))


class RoleFactory(BaseFactory):
    class Meta:
        model = Role

    name = factory.Faker("bothify", text="role_????")
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        admin = factory.Trait(name="admin")
        user = factory.Trait(name="user")
        guest = factory.Trait(name="guest")
        moderator = factory.Trait(name="moderator")


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("name", locale="fr_FR")
    role_id = None
    role = factory.SubFactory(RoleFactory)
    sub = None
    organization_id = None
    organization = factory.SubFactory(OrganizationFactory)
    password = "$2b$12$I7iMWv/FqLtb7Az6iX9uTuPkvGWU1xh.Gtwb3qb0.fm8kCYJkLRwq"
    iss = None
    priority = 0
    expires = None
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    @factory.lazy_attribute
    def email(self):
        from faker import Faker

        name_normalized = unicodedata.normalize("NFKD", self.name)
        name_ascii = name_normalized.encode("ascii", "ignore").decode("ascii")
        fake = Faker("fr_FR")
        domain = fake.free_email_domain()
        clean_name = name_ascii.lower().replace(" ", ".")
        return f"{clean_name}@e{domain}"

    class Params:
        admin_user = factory.Trait(role=factory.SubFactory(RoleFactory, admin=True), priority=10)
        regular_user = factory.Trait(role=factory.SubFactory(RoleFactory, user=True), priority=0)
        guest_user = factory.Trait(role=factory.SubFactory(RoleFactory, guest=True), priority=-1)


class TokenFactory(BaseFactory):
    class Meta:
        model = Token

    user_id = None
    user = factory.SubFactory(UserFactory)
    name = factory.Faker("word")
    token = "tmp"
    expires = factory.LazyFunction(lambda: datetime.now() + timedelta(days=30))
    created = factory.LazyFunction(lambda: datetime.now())

    class Params:
        expired = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() - timedelta(days=1)))

        never_expires = factory.Trait(expires=None)

        short_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() + timedelta(hours=1)))

        long_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() + timedelta(days=365)))


class TokenForUserFactory(TokenFactory):
    """Factory for creating tokens for an existing user."""

    @classmethod
    def create_for_user(cls, user, **kwargs):
        """Create a token for a specific user."""
        return cls(user=user, **kwargs)


class RouterFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Router
        sqlalchemy_session_persistence = "flush"

    user_id = None
    id = None
    user = factory.SubFactory(UserFactory)
    name = factory.Faker("bothify", text="router_####")
    type = factory.Faker("random_element", elements=list(ModelType))
    load_balancing_strategy = factory.Faker("random_element", elements=list(RouterLoadBalancingStrategy))
    cost_prompt_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    cost_completion_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        free = factory.Trait(cost_prompt_tokens=0.0, cost_completion_tokens=0.0)
        expensive = factory.Trait(
            cost_prompt_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0.5, max_value=2),
            cost_completion_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=1, max_value=3),
        )


class RouterAliasFactory(BaseFactory):
    class Meta:
        model = RouterAlias

    router_id = None
    router = factory.SubFactory(RouterFactory)
    value = factory.Faker("bothify", text="alias_????_####")


class ProviderFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Provider
        sqlalchemy_session_persistence = "flush"

    id = None
    router_id = None
    router = factory.SubFactory(RouterFactory)
    user_id = None
    user = factory.SubFactory(UserFactory)
    type = factory.Faker("random_element", elements=list(ProviderType))
    url = factory.Faker("bothify", text="https://provider-##.example.com")
    key = factory.Faker("uuid4")
    timeout = factory.Faker("random_int", min=1, max=300)
    model_name = factory.Faker("bothify", text="model-##-?????")
    model_carbon_footprint_zone = factory.Faker("random_element", elements=list(ProviderCarbonFootprintZone))
    model_carbon_footprint_total_params = factory.Faker("random_int", min=1000000, max=2000000000)
    model_carbon_footprint_active_params = factory.Faker("random_int", min=1000000, max=1000000000)
    qos_metric = factory.Faker("random_element", elements=list(Metric))
    qos_limit = factory.Faker("pyfloat", left_digits=2, right_digits=2, min_value=0.5, max_value=0.99)
    max_context_length = factory.Faker("random_element", elements=[2048, 4096, 8192, 16384, 32768, 128000])
    vector_size = factory.Faker("random_element", elements=[384, 768, 1024, 1536, 3072])
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        openai_like = factory.Trait(
            type=ProviderType.OPENAI if hasattr(ProviderType, "OPENAI") else factory.Faker("random_element", elements=list(ProviderType)),
            url="https://api.openai.com/v1",
            model_name="gpt-4",
            max_context_length=8192,
        )

        no_qos = factory.Trait(qos_metric=None, qos_limit=None)

        minimal = factory.Trait(
            key=None,
            timeout=None,
            model_carbon_footprint_zone=None,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
            qos_metric=None,
            qos_limit=None,
            max_context_length=None,
            vector_size=None,
        )

        embedding = factory.Trait(model_name="text-embedding-ada-002", vector_size=1536, max_context_length=8191)

        large_model = factory.Trait(model_carbon_footprint_total_params=2000000000, model_carbon_footprint_active_params=1000000000)

        small_model = factory.Trait(model_carbon_footprint_total_params=100000000, model_carbon_footprint_active_params=50000000)


class ProviderForRouterFactory(ProviderFactory):
    """Factory for creating providers for an existing router."""

    @classmethod
    def create_for_router(cls, router, **kwargs):
        """Create a provider for a specific router."""
        return cls.create(router=router, **kwargs)

    @classmethod
    def create_for_router_and_user(cls, router, user, **kwargs):
        """Create a provider for a specific router."""
        return cls.create(router=router, user=user, user_id=user.id, **kwargs)


class LimitFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Limit
        sqlalchemy_session_persistence = "flush"

    id = None
    role_id = factory.SelfAttribute("role.id")
    router_id = factory.SelfAttribute("router.id")
    type = fuzzy.FuzzyChoice([LimitType.TPM, LimitType.TPD, LimitType.RPM, LimitType.RPD])
    value = fuzzy.FuzzyInteger(100, 10000)
    created = factory.LazyFunction(datetime.now)

    role = factory.SubFactory(RoleFactory)
    router = factory.SubFactory(RouterFactory)


class UserInfoFactory(factory.Factory):
    class Meta:
        model = UserInfo

    id = factory.Sequence(lambda n: n + 1)
    email = factory.Faker("email")
    name = factory.Faker("name")
    organization = factory.Faker("random_int", min=1, max=1000)
    budget = factory.Faker("pyfloat", left_digits=5, right_digits=2, positive=True)

    @factory.lazy_attribute
    def permissions(self):
        all_perms = list(PermissionType)
        return random.sample(all_perms, k=random.randint(1, len(all_perms)))

    @factory.lazy_attribute
    def limits(self):
        return [LimitFactory() for _ in range(random.randint(1, 3))]

    expires = factory.LazyFunction(lambda: int((datetime.now() + timedelta(days=365)).timestamp()))
    priority = factory.Faker("random_int", min=0, max=10)
    created = factory.LazyFunction(lambda: int(datetime.now().timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now().timestamp()))

    class Params:
        unlimited_budget = factory.Trait(budget=None)

        no_expiration = factory.Trait(expires=None)

        admin = factory.Trait(permissions=[PermissionType.ADMIN])

        no_organization = factory.Trait(organization=None, name=None)
