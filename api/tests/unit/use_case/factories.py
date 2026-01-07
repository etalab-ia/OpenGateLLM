from datetime import UTC, datetime, timedelta
import random
import unicodedata

import factory
from factory import fuzzy

from api.domain.role.entities import Limit, LimitType, PermissionType, Role
from api.domain.router.entities import Router
from api.domain.user.entities import User
from api.domain.userinfo.entities import UserInfo
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.models import ModelType


class RoleFactory(factory.Factory):
    class Meta:
        model = Role

    name = factory.Faker("bothify", text="role_????")
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))

    class Params:
        admin = factory.Trait(name="admin")
        user = factory.Trait(name="user")
        guest = factory.Trait(name="guest")
        moderator = factory.Trait(name="moderator")


class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Faker("name", locale="fr_FR")
    role_id = None
    role = factory.SubFactory(RoleFactory)
    sub = None
    organization = factory.Faker("random_int", min=1, max=10000)
    password = "$2b$12$I7iMWv/FqLtb7Az6iX9uTuPkvGWU1xh.Gtwb3qb0.fm8kCYJkLRwq"
    iss = None
    priority = 0
    expires = None
    created = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))
    updated = factory.LazyFunction(lambda: int(datetime.now(UTC).timestamp()))

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


class RouterFactory(factory.Factory):
    class Meta:
        model = Router

    id = None
    user_id = None
    name = factory.Faker("bothify", text="router_####")
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

        with_aliases = factory.Trait(
            aliases=factory.LazyFunction(
                lambda: [factory.Faker("bothify", text="alias_####").generate(), factory.Faker("bothify", text="alias_####").generate()]
            )
        )

        with_providers = factory.Trait(providers=factory.Faker("random_int", min=1, max=5))


class LimitFactory(factory.Factory):
    class Meta:
        model = Limit

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
