from datetime import UTC, datetime, timedelta
import random

import factory
from factory import fuzzy

from api.domain.role.entities import Limit, LimitType, PermissionType, Role
from api.domain.router.entities import ModelType, Router, RouterLoadBalancingStrategy
from api.domain.user.entities import User
from api.domain.userinfo.entities import UserInfo


class LimitFactory(factory.Factory):
    class Meta:
        model = Limit

    router = factory.Faker("random_int", min=1, max=1000)
    type = fuzzy.FuzzyChoice([LimitType.TPM, LimitType.TPD, LimitType.RPM, LimitType.RPD])
    value = fuzzy.FuzzyInteger(100, 10000)


class RoleFactory(factory.Factory):
    class Meta:
        model = Role

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("bothify", text="role_????")
    permissions = factory.LazyFunction(lambda: random.sample(list(PermissionType), k=random.randint(0, len(PermissionType))))
    limits = factory.LazyFunction(list)
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))

    class Params:
        admin = factory.Trait(name="admin", permissions=[PermissionType.ADMIN])
        user = factory.Trait(name="user")


class RouterFactory(factory.Factory):
    class Meta:
        model = Router

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("bothify", text="router_####")
    user_id = factory.Faker("random_int", min=1, max=1000)
    type = factory.Faker("random_element", elements=list(ModelType))
    aliases = None
    load_balancing_strategy = factory.Faker("random_element", elements=list(RouterLoadBalancingStrategy))
    vector_size = None
    max_context_length = None
    cost_prompt_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    cost_completion_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    providers = 0
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))

    class Params:
        free = factory.Trait(cost_prompt_tokens=0.0, cost_completion_tokens=0.0)

        expensive = factory.Trait(
            cost_prompt_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0.5, max_value=2),
            cost_completion_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=1, max_value=3),
        )

        embedding = factory.Trait(
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            vector_size=factory.Faker("random_element", elements=[384, 768, 1536, 3072]),
            max_context_length=factory.Faker("random_element", elements=[512, 1024, 2048, 8192]),
        )

        with_providers = factory.Trait(providers=factory.Faker("random_int", min=1, max=5))


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n + 1)
    email = factory.Faker("email")
    name = factory.Faker("name", locale="fr_FR")
    sub = None
    iss = None
    role = factory.Faker("random_int", min=1, max=100)
    organization = factory.Faker("random_int", min=1, max=10000)
    budget = factory.Faker("pyfloat", left_digits=5, right_digits=2, positive=True)
    expires = None
    priority = 0
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))


class UserInfoFactory(factory.Factory):
    class Meta:
        model = UserInfo

    id = factory.Sequence(lambda n: n + 1)
    email = factory.Faker("email")
    name = factory.Faker("name")
    organization = factory.Faker("random_int", min=1, max=1000)
    budget = factory.Faker("pyfloat", left_digits=5, right_digits=2, positive=True)
    permissions = factory.LazyFunction(lambda: random.sample(list(PermissionType), k=random.randint(1, len(PermissionType))))
    limits = factory.LazyFunction(lambda: [LimitFactory() for _ in range(random.randint(1, 3))])
    expires = factory.LazyFunction(lambda: int((datetime.now(UTC) + timedelta(days=365)).timestamp()))
    priority = factory.Faker("random_int", min=0, max=10)
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))

    class Params:
        unlimited_budget = factory.Trait(budget=None)
        no_expiration = factory.Trait(expires=None)
        admin = factory.Trait(permissions=[PermissionType.ADMIN])
        without_permission = factory.Trait(permissions=[])
        no_organization = factory.Trait(organization=None, name=None)
