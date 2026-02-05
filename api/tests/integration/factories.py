from datetime import datetime, timedelta
import unicodedata

import factory
from factory import fuzzy
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from api.domain.role.entities import LimitType, PermissionType
from api.schemas.admin.providers import ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.models import Metric
from api.schemas.models import ModelType
from api.sql.models import Limit, Organization, Permission, Provider, Role, Router, RouterAlias, Token, User


class BaseSQLFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"


class OrganizationSQLFactory(BaseSQLFactory):
    class Meta:
        model = Organization

    name = factory.Faker("company", locale="fr_FR")
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        administration = factory.Trait(name=factory.Faker("bothify", text="Administration ####"))
        ministere = factory.Trait(name=factory.Faker("bothify", text="Ministere ####"))


class RoleSQLFactory(BaseSQLFactory):
    class Meta:
        model = Role

    name = factory.Faker("bothify", text="role_????")
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    class Params:
        admin = factory.Trait(
            name="admin",
            admin_permission=factory.RelatedFactory(
                "api.tests.integration.factories.PermissionSQLFactory",
                factory_related_name="role",
                permission=PermissionType.ADMIN,
            ),
        )
        user = factory.Trait(name="user")
        guest = factory.Trait(name="guest")
        moderator = factory.Trait(name="moderator")


class PermissionSQLFactory(BaseSQLFactory):
    class Meta:
        model = Permission

    role_id = None
    role = factory.SubFactory(RoleSQLFactory)
    permission = factory.Faker("random_element", elements=list(PermissionType))
    created = factory.LazyFunction(lambda: datetime.now())

    class Params:
        admin = factory.Trait(
            permission=PermissionType.ADMIN,
            role=factory.SubFactory(RoleSQLFactory, admin=True),
        )
        create_public_collection = factory.Trait(permission=PermissionType.CREATE_PUBLIC_COLLECTION)
        read_metric = factory.Trait(permission=PermissionType.READ_METRIC)
        provide_models = factory.Trait(permission=PermissionType.PROVIDE_MODELS)


class UserSQLFactory(BaseSQLFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("name", locale="fr_FR")
    role_id = None
    id = None
    role = factory.SubFactory(RoleSQLFactory)
    sub = None
    organization_id = None
    organization = factory.SubFactory(OrganizationSQLFactory)
    password = "$2b$12$I7iMWv/FqLtb7Az6iX9uTuPkvGWU1xh.Gtwb3qb0.fm8kCYJkLRwq"
    iss = None
    priority = 0
    expires = None
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    @factory.lazy_attribute
    def email(self):
        name_normalized = unicodedata.normalize("NFKD", self.name)
        name_ascii = name_normalized.encode("ascii", "ignore").decode("ascii")
        fake = Faker("fr_FR")
        domain = fake.free_email_domain()
        clean_name = name_ascii.lower().replace(" ", ".")
        return f"{clean_name}@e{domain}"

    class Params:
        admin_user = factory.Trait(role=factory.SubFactory(RoleSQLFactory, admin=True), priority=10)
        regular_user = factory.Trait(role=factory.SubFactory(RoleSQLFactory, user=True), priority=0)
        guest_user = factory.Trait(role=factory.SubFactory(RoleSQLFactory, guest=True), priority=-1)


class TokenSQLFactory(BaseSQLFactory):
    class Meta:
        model = Token

    user_id = None
    user = factory.SubFactory(UserSQLFactory)
    name = factory.Faker("word")
    token = "tmp"
    expires = factory.LazyFunction(lambda: datetime.now() + timedelta(days=30))
    created = factory.LazyFunction(lambda: datetime.now())

    class Params:
        expired = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() - timedelta(days=1)))

        never_expires = factory.Trait(expires=None)

        short_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() + timedelta(hours=1)))

        long_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.now() + timedelta(days=365)))


class RouterSQLFactory(BaseSQLFactory):
    class Meta:
        model = Router
        sqlalchemy_session_persistence = "flush"

    user_id = None
    id = None
    user = factory.SubFactory(UserSQLFactory)
    name = factory.Faker("bothify", text="router_####")
    type = factory.Faker("random_element", elements=list(ModelType))
    load_balancing_strategy = factory.Faker("random_element", elements=list(RouterLoadBalancingStrategy))
    cost_prompt_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    cost_completion_tokens = factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0, max_value=1)
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())

    @factory.post_generation
    def alias(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for alias_value in extracted:
            RouterAliasSQLFactory(router=self, value=alias_value)

    @factory.post_generation
    def providers(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for i in range(extracted):
            ProviderSQLFactory(router=self, user=self.user, model_name=f"{self.name}_provider_{i + 1}", **kwargs)

    class Params:
        free = factory.Trait(cost_prompt_tokens=0.0, cost_completion_tokens=0.0)
        expensive = factory.Trait(
            cost_prompt_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=0.5, max_value=2),
            cost_completion_tokens=factory.Faker("pyfloat", left_digits=1, right_digits=4, min_value=1, max_value=3),
        )


class RouterAliasSQLFactory(BaseSQLFactory):
    class Meta:
        model = RouterAlias

    router_id = None
    router = factory.SubFactory(RouterSQLFactory)
    value = factory.Faker("bothify", text="alias_????_####")


class ProviderSQLFactory(BaseSQLFactory):
    class Meta:
        model = Provider
        sqlalchemy_session_persistence = "flush"

    id = None
    router_id = None
    router = factory.SubFactory(RouterSQLFactory)
    user_id = None
    user = factory.LazyAttribute(lambda o: o.router.user)
    type = factory.Faker("random_element", elements=list(ProviderType))
    url = factory.Faker("bothify", text="https://provider-##.example.com")
    key = factory.Faker("uuid4")
    timeout = factory.Faker("random_int", min=1, max=300)
    model_name = factory.Faker("bothify", text="model-##-?????")
    model_hosting_zone = factory.Faker("random_element", elements=list(ProviderCarbonFootprintZone))
    model_total_params = factory.Faker("random_int", min=1000000, max=2000000000)
    model_active_params = factory.Faker("random_int", min=1000000, max=1000000000)
    qos_metric = factory.Faker("random_element", elements=list(Metric))
    qos_limit = factory.Faker("pyfloat", left_digits=2, right_digits=2, min_value=0.5, max_value=0.99)
    max_context_length = factory.Faker("random_element", elements=[2048, 4096, 8192, 16384, 32768, 128000])
    vector_size = factory.Faker("random_element", elements=[384, 768, 1024, 1536, 3072])
    created = factory.LazyFunction(lambda: datetime.now())
    updated = factory.LazyFunction(lambda: datetime.now())


class LimitSQLFactory(BaseSQLFactory):
    class Meta:
        model = Limit
        sqlalchemy_session_persistence = "flush"

    id = None
    role_id = factory.SelfAttribute("role.id")
    router_id = factory.SelfAttribute("router.id")
    type = fuzzy.FuzzyChoice([LimitType.TPM, LimitType.TPD, LimitType.RPM, LimitType.RPD])
    value = fuzzy.FuzzyInteger(100, 10000)
    created = factory.LazyFunction(datetime.now)

    role = factory.SubFactory(RoleSQLFactory)
    router = factory.SubFactory(RouterSQLFactory)
