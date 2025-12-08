from datetime import datetime, timedelta

import factory
from factory.alchemy import SQLAlchemyModelFactory

from api.sql.models import Role, Token, User


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class RoleFactory(BaseFactory):
    class Meta:
        model = Role

    name = factory.Faker("bothify", text="role_????")
    created = factory.LazyFunction(datetime.utcnow)
    updated = factory.LazyFunction(datetime.utcnow)

    class Params:
        admin = factory.Trait(name="admin")
        user = factory.Trait(name="user")
        guest = factory.Trait(name="guest")
        moderator = factory.Trait(name="moderator")


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker("email")
    role_id = None
    role = factory.SubFactory(RoleFactory)
    email = factory.Faker("email")
    sub = None
    organization_id = None
    password = "$2b$12$I7iMWv/FqLtb7Az6iX9uTuPkvGWU1xh.Gtwb3qb0.fm8kCYJkLRwq"  # hashed "password"
    iss = None
    priority = 0
    expires = None
    created = factory.LazyFunction(datetime.utcnow)
    updated = factory.LazyFunction(datetime.utcnow)

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
    expires = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=30))
    created = factory.LazyFunction(datetime.utcnow)

    class Params:
        expired = factory.Trait(expires=factory.LazyFunction(lambda: datetime.utcnow() - timedelta(days=1)))

        never_expires = factory.Trait(expires=None)

        short_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.utcnow() + timedelta(hours=1)))

        long_lived = factory.Trait(expires=factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=365)))


class TokenForUserFactory(TokenFactory):
    """Factory for creating tokens for an existing user."""

    @classmethod
    def create_for_user(cls, user, **kwargs):
        """Create a token for a specific user."""
        return cls(user=user, **kwargs)
