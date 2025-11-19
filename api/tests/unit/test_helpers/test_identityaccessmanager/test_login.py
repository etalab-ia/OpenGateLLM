from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.schemas.admin.roles import Limit, LimitType, PermissionType
from api.schemas.me.info import UserInfo
from api.utils.exceptions import InvalidCurrentPasswordException, UserNotFoundException


@pytest.fixture
def postgres_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def iam():
    return IdentityAccessManager(master_key="secret")


class _Result:
    def __init__(self, scalar_one=None, all_rows=None, iterate_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows
        self._iterate_rows = iterate_rows

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

    def __iter__(self):
        return iter(self._iterate_rows or [])


@pytest.mark.asyncio
async def test_login_success_master(postgres_session: AsyncSession, iam: IdentityAccessManager):
    token_id, token = await iam.login(postgres_session=postgres_session, email="master", password="secret")
    assert token_id == 0
    assert token == "secret"


@pytest.mark.asyncio
async def test_login_success_user(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Prepare a real password and its hash stored in DB
    password_plain = "correcthorsebatterystaple"
    hashed = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Mock get_user_info to return a valid user
    from api.schemas.me.info import UserInfo

    iam.get_user_info = AsyncMock(
        return_value=UserInfo(
            id=1,
            email="alice@example.com",
            name="alice",
            organization=None,
            budget=None,
            permissions=[PermissionType.READ_METRIC],
            limits=[Limit(router=1, type=LimitType.TPM, value=100)],
            expires=None,
            created=10,
            updated=11,
        )
    )

    # DB returns the hashed password
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=hashed))

    # Mock refresh_token to avoid deeper DB interactions
    iam.refresh_token = AsyncMock(return_value=(123, "tok-xyz"))

    token_id, token = await iam.login(postgres_session=postgres_session, email="alice@example.com", password=password_plain)
    assert token_id == 123
    assert token == "tok-xyz"


@pytest.mark.asyncio
async def test_login_user_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Make get_user_info raise the expected exception
    iam.get_user_info = AsyncMock(side_effect=UserNotFoundException())

    with pytest.raises(UserNotFoundException):
        await iam.login(postgres_session=postgres_session, email="nonexistent@example.com", password="whatever")


@pytest.mark.asyncio
async def test_login_wrong_password(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Mock a user and DB password retrieval

    iam.get_user_info = AsyncMock(
        return_value=UserInfo(
            id=1,
            email="alice@example.com",
            name="alice",
            organization=None,
            budget=None,
            permissions=[],
            limits=[],
            expires=None,
            created=0,
            updated=0,
        )
    )
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one="hashed"))

    # Force password check to raise the expected exception
    iam._check_password = MagicMock(side_effect=InvalidCurrentPasswordException())

    with pytest.raises(InvalidCurrentPasswordException):
        await iam.login(postgres_session=postgres_session, email="alice@example.com", password="wrong")


@pytest.mark.asyncio
async def test_login_missing_inputs_raises(postgres_session: AsyncSession, iam: IdentityAccessManager):
    with pytest.raises(AssertionError):
        await iam.login(postgres_session=postgres_session, email=None, password=None)
