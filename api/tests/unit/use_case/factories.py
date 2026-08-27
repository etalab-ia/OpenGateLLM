from datetime import UTC, datetime, timedelta
import random

import factory
from factory import fuzzy

from api.domain.model.entities import ModelCosts
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.views import ModelView
from api.domain.organization.entities import Organization
from api.domain.provider.entities import BasicAuth, HostingZone, Provider, ProviderType
from api.domain.role.entities import Limit, LimitType, PermissionType, Role
from api.domain.router.entities import Router, RouterLoadBalancingStrategy
from api.domain.user.entities import User
from api.domain.user.views import AuthenticatedUserView
from api.schemas.core.configuration import Model as ModelConfiguration
from api.schemas.core.configuration import ModelProvider as ModelProviderConfiguration


# Entity factories
class LimitFactory(factory.Factory):
    class Meta:
        model = Limit

    router_id = factory.Faker("random_int", min=1, max=1000)
    type = fuzzy.FuzzyChoice([LimitType.TPM, LimitType.TPD, LimitType.RPM, LimitType.RPD])
    value = fuzzy.FuzzyInteger(100, 10000)


class RoleFactory(factory.Factory):
    class Meta:
        model = Role

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("bothify", text="role_????")
    permissions = factory.LazyFunction(lambda: random.sample(list(PermissionType), k=random.randint(0, len(PermissionType))))
    limits = factory.LazyFunction(list)
    created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated = factory.LazyFunction(lambda: datetime.now(tz=UTC))

    class Params:
        admin = factory.Trait(name="admin", permissions=[PermissionType.ADMIN])
        user = factory.Trait(name="user")


class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("bothify", text="organization_????")
    users = 0
    created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated = factory.LazyFunction(lambda: datetime.now(tz=UTC))


class RouterFactory(factory.Factory):
    class Meta:
        model = Router

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("bothify", text="router_####")
    user_id = factory.Faker("random_int", min=1, max=1000)
    type = factory.Faker("random_element", elements=list(RouterType))
    aliases = None
    load_balancing_strategy = factory.Faker("random_element", elements=list(RouterLoadBalancingStrategy))
    cost_prompt_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    cost_completion_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    providers = 0
    created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated = factory.LazyFunction(lambda: datetime.now(tz=UTC))

    class Params:
        free = factory.Trait(cost_prompt_tokens=0.0, cost_completion_tokens=0.0)

        expensive = factory.Trait(
            cost_prompt_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0.5, max_value=2),
            cost_completion_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=1, max_value=3),
        )

        embedding = factory.Trait(type=RouterType.TEXT_EMBEDDINGS_INFERENCE)

        with_providers = factory.Trait(providers=factory.Faker("random_int", min=1, max=5))


class ProviderFactory(factory.Factory):
    class Meta:
        model = Provider

    id = factory.Sequence(lambda n: n + 1)
    router_id = factory.Faker("random_int", min=1, max=1000)
    user_id = factory.Faker("random_int", min=1, max=1000)
    type = factory.Faker("random_element", elements=list(ProviderType))
    url = factory.Faker("url")
    key = None
    basic_auth = None
    timeout = 30
    model_name = factory.Faker("bothify", text="model-????")
    model_hosting_zone = HostingZone.WOR
    model_total_params = 0
    model_active_params = 0
    qos_metric = None
    qos_limit = None
    max_context_length = None
    vector_size = None
    created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated = factory.LazyFunction(lambda: datetime.now(tz=UTC))


class ModelViewFactory(factory.Factory):
    class Meta:
        model = ModelView

    router_id = factory.Sequence(lambda n: n + 1)
    id = factory.Faker("bothify", text="model-????")
    type = factory.Faker("random_element", elements=list(RouterType))
    aliases = factory.LazyFunction(list)
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    owned_by = factory.Faker("bothify", text="organization_????")
    max_context_length = None
    costs = factory.LazyFunction(ModelCosts)


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n + 1)
    email = factory.Faker("email")
    name = factory.Faker("name", locale="fr_FR")
    password = None
    sub = None
    iss = None
    claims = None
    role_id = factory.Faker("random_int", min=1, max=100)
    organization_id = factory.Faker("random_int", min=1, max=10000)
    budget = factory.Faker("pyfloat", left_digits=5, right_digits=2, positive=True)
    expires = None
    priority = 0
    created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated = factory.LazyFunction(lambda: datetime.now(tz=UTC))


class AuthenticatedUserFactory(factory.Factory):
    class Meta:
        model = AuthenticatedUserView

    id = factory.Sequence(lambda n: n + 1)
    email = factory.Faker("email")
    name = factory.Faker("name")
    organization_id = factory.Faker("random_int", min=1, max=1000)
    budget = factory.Faker("pyfloat", left_digits=5, right_digits=2, positive=True)
    permissions = factory.LazyFunction(lambda: random.sample(list(PermissionType), k=random.randint(1, len(PermissionType))))
    limits = factory.LazyFunction(lambda: [LimitFactory() for _ in range(random.randint(1, 3))])
    expires = factory.LazyFunction(lambda: datetime.now(tz=UTC) + timedelta(days=365))

    class Params:
        unlimited_budget = factory.Trait(budget=None)
        no_expiration = factory.Trait(expires=None)
        admin = factory.Trait(permissions=[PermissionType.ADMIN])
        without_permission = factory.Trait(permissions=[])
        no_organization = factory.Trait(organization_id=None, name=None)


# Configuration factories
class ModelProviderConfigurationFactory(factory.Factory):
    class Meta:
        model = ModelProviderConfiguration

    type = ProviderType.VLLM
    url = factory.Faker("url")
    key = None
    basic_auth: BasicAuth | None = None
    timeout = 30
    model_name = factory.Faker("bothify", text="model-????")
    model_hosting_zone = HostingZone.WOR
    model_total_params = 0
    model_active_params = 0
    qos_metric = None
    qos_limit = None

    class Params:
        tei = factory.Trait(type=ProviderType.TEI)
        openai = factory.Trait(type=ProviderType.OPENAI)
        albert = factory.Trait(type=ProviderType.ALBERT)


class ModelConfigurationFactory(factory.Factory):
    class Meta:
        model = ModelConfiguration

    name = factory.Faker("bothify", text="router_####")
    type = RouterType.TEXT_GENERATION
    aliases = factory.LazyFunction(list)
    load_balancing_strategy = RouterLoadBalancingStrategy.SHUFFLE
    cost_prompt_tokens = 0.0
    cost_completion_tokens = 0.0
    providers = factory.LazyFunction(lambda: [ModelProviderConfigurationFactory()])

    class Params:
        embedding = factory.Trait(
            type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            providers=factory.LazyFunction(lambda: [ModelProviderConfigurationFactory(tei=True)]),
        )
