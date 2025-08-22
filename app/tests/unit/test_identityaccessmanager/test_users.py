import datetime as dt
import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.utils.exceptions import (
    OrganizationNotFoundException,
    RoleNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
import bcrypt


class _Result:
    def __init__(self, scalar_one=None, all_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows

    def scalar_one(self):
        if isinstance(self._scalar_one, Exception):
            raise self._scalar_one
        return self._scalar_one

    def scalar_one_or_none(self):
        # mirror SQLAlchemy behavior: raise if exception, otherwise return value (may be None)
        if isinstance(self._scalar_one, Exception):
            raise self._scalar_one
        return self._scalar_one

    def all(self):
        return self._all_rows or []


@pytest.fixture
def session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def iam():
    return IdentityAccessManager(master_key="secret")


@pytest.mark.asyncio
async def test_create_user_success(session: AsyncSession, iam: IdentityAccessManager):
    # role exists -> ok, organization None, insert -> returning id
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=10)])

    uid = await iam.create_user(
        session=session,
        name="alice",
        role_id=1,
        organization_id=None,
        budget=12.5,
        expires_at=int(dt.datetime.now(tz=dt.UTC).timestamp()) + 100,
        sub="sub123",
        email="alice@example.com",
    )

    assert uid == 10
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_user_role_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(RoleNotFoundException):
        await iam.create_user(session, name="bob", role_id=9)


@pytest.mark.asyncio
async def test_create_user_organization_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=NoResultFound())])

    with pytest.raises(OrganizationNotFoundException):
        await iam.create_user(session, name="bob", role_id=1, organization_id=5)


@pytest.mark.asyncio
async def test_create_user_unique_violation_to_400(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), IntegrityError("", "", None)])

    with pytest.raises(UserAlreadyExistsException):
        await iam.create_user(session, name="bob", role_id=1)


@pytest.mark.asyncio
async def test_delete_user_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(UserNotFoundException):
        await iam.delete_user(session, user_id=404)


@pytest.mark.asyncio
async def test_delete_user_success(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), None])
    await iam.delete_user(session, user_id=1)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_user_success_all_fields(session: AsyncSession, iam: IdentityAccessManager):
    # select user with join role
    session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires_at=None, role="role")]),
            _Result(scalar_one=1),  # check new role exists when different
            _Result(scalar_one=1),  # check organization exists
            None,  # update
        ]
    )

    await iam.update_user(
        session=session,
        user_id=1,
        name="alice2",
        role_id=2,
        organization_id=3,
        budget=100.0,
        expires_at=int(dt.datetime.now(tz=dt.UTC).timestamp()) + 100,
    )

    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_user_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(UserNotFoundException):
        await iam.update_user(session, user_id=123)


@pytest.mark.asyncio
async def test_update_user_role_missing(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires_at=None, role="role")]),
            _Result(scalar_one=NoResultFound()),
        ]
    )

    with pytest.raises(RoleNotFoundException):
        await iam.update_user(session, user_id=1, role_id=9)


@pytest.mark.asyncio
async def test_update_user_org_missing(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires_at=None, role="role")]),
            _Result(scalar_one=NoResultFound()),  # organization lookup -> not found
        ]
    )

    with pytest.raises(OrganizationNotFoundException):
        await iam.update_user(session, user_id=1, role_id=1, organization_id=999)


@pytest.mark.asyncio
async def test_get_users_filters_and_not_found(session: AsyncSession, iam: IdentityAccessManager):
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires_at": None,
                "created_at": 10,
                "updated_at": 11,
                "email": "alice@example.com",
                "sub": "sub",
            }
        )
    ]
    session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    users = await iam.get_users(session, role_id=1)
    assert len(users) == 1
    assert users[0].name == "alice"

    # not found by id
    session.execute = AsyncMock(return_value=_Result(all_rows=[]))
    with pytest.raises(UserNotFoundException):
        await iam.get_users(session, user_id=404)


@pytest.mark.asyncio
async def test_verify_user_credentials_success(session: AsyncSession, iam: IdentityAccessManager):
    # create a fake user object with a bcrypt-hashed password
    password_plain = "correcthorsebatterystaple"
    hashed = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    fake_user = MagicMock(id=1, email="alice@example.com", password=hashed)

    session.execute = AsyncMock(return_value=_Result(scalar_one=fake_user))

    user = await iam.verify_user_credentials(session=session, email="alice@example.com", password=password_plain)
    assert user is not None
    assert user.id == 1


@pytest.mark.asyncio
async def test_verify_user_credentials_wrong_password(session: AsyncSession, iam: IdentityAccessManager):
    password_plain = "correcthorsebatterystaple"
    hashed = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    fake_user = MagicMock(id=1, email="alice@example.com", password=hashed)

    session.execute = AsyncMock(return_value=_Result(scalar_one=fake_user))

    user = await iam.verify_user_credentials(session=session, email="alice@example.com", password="wrongpassword")
    assert user is None


@pytest.mark.asyncio
async def test_verify_user_credentials_user_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=None))

    user = await iam.verify_user_credentials(session=session, email="nonexistent@example.com", password="whatever")
    assert user is None


@pytest.mark.asyncio
async def test_verify_user_credentials_missing_inputs(session: AsyncSession, iam: IdentityAccessManager):
    user = await iam.verify_user_credentials(session=session, email=None, password=None)
    assert user is None
