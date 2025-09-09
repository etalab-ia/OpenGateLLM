import datetime as dt
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from jose import JWTError
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.utils.exceptions import (
    InvalidTokenExpirationException,
    TokenNotFoundException,
    UserNotFoundException,
)


class _Result:
    def __init__(self, scalar_one=None, all_rows=None, iterate_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows
        self._iterate_rows = iterate_rows

    def scalar_one(self):
        if isinstance(self._scalar_one, Exception):
            raise self._scalar_one
        return self._scalar_one

    def all(self):
        return self._all_rows or []

    def __iter__(self):
        return iter(self._iterate_rows or [])


@pytest.fixture
def session():
    return AsyncMock(spec=AsyncSession)


def _ts_now():
    return int(dt.datetime.now(tz=dt.UTC).timestamp())


@pytest.mark.asyncio
async def test_create_token_success_and_masking(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret", max_token_expiration_days=10)

    # user exists
    session.execute = AsyncMock()
    session.execute.side_effect = [
        _Result(scalar_one=MagicMock(id=1)),  # select user
        _Result(scalar_one=123),  # insert token, returning id
        None,  # update token with masked token
    ]

    with patch.object(iam, "_encode_token", return_value="sk-abc123456789xyz") as enc:
        token_id, app_token = await iam.create_token(session, user_id=1, name="dev", expires_at=_ts_now() + 100)

    assert token_id == 123
    assert app_token.startswith("sk-")
    enc.assert_called_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_token_user_not_found(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(UserNotFoundException):
        await iam.create_token(session, user_id=99, name="dev")


@pytest.mark.asyncio
async def test_create_token_invalid_expiration_window(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret", max_token_expiration_days=1)
    session.execute = AsyncMock(return_value=_Result(scalar_one=MagicMock(id=1)))

    too_far = _ts_now() + 3 * 86400

    with pytest.raises(InvalidTokenExpirationException):
        await iam.create_token(session, user_id=1, name="dev", expires_at=too_far)


@pytest.mark.asyncio
async def test_refresh_token_updates_usage_and_deletes_old(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    # old tokens with same name
    session.execute = AsyncMock()
    session.execute.side_effect = [
        _Result(all_rows=[(10,), (11,)]),  # select old token ids
        _Result(scalar_one=MagicMock(id=1)),  # select user in create_token
        _Result(scalar_one=100),  # insert new token id
        None,  # update new token with masked token
        None,  # update usage set token_id to new
        None,  # delete old tokens
    ]

    with patch.object(iam, "_encode_token", return_value="sk-newtoken"):
        new_id, app_token = await iam.refresh_token(session, user_id=1, name="dev", duration=3600)

    assert new_id == 100
    assert app_token == "sk-newtoken"
    assert session.commit.await_count >= 2


@pytest.mark.asyncio
async def test_delete_token_not_found(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(TokenNotFoundException):
        await iam.delete_token(session, user_id=1, token_id=9)


@pytest.mark.asyncio
async def test_delete_token_success(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), None])

    await iam.delete_token(session, user_id=1, token_id=2)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_tokens_by_name(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(return_value=None)
    await iam.delete_tokens(session, user_id=1, name="ci")
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_tokens_filters_and_exclude_expired(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    rows = [
        MagicMock(_mapping={"id": 1, "name": "dev", "token": "sk-xxxx", "user": 1, "expires_at": None, "created_at": 10}),
        MagicMock(_mapping={"id": 2, "name": "ops", "token": "sk-yyyy", "user": 1, "expires_at": 11, "created_at": 12}),
    ]
    session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    tokens = await iam.get_tokens(session, user_id=1, exclude_expired=True)

    assert len(tokens) == 2
    assert tokens[0].user == 1


@pytest.mark.asyncio
async def test_get_token_by_id_not_found(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(TokenNotFoundException):
        await iam.get_tokens(session, token_id=404)


@pytest.mark.asyncio
async def test_check_token_ok(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    with patch.object(iam, "_decode_token", return_value={"user_id": 1, "token_id": 2}):
        session.execute = AsyncMock(
            return_value=_Result(
                all_rows=[
                    MagicMock(
                        _mapping={
                            "id": 2,
                            "user": 1,
                            "token": "sk-abcdef",
                            "name": "dev",
                            "created_at": 1755243926,
                            "expires_at": None,
                        }
                    )
                ]
            )
        )
        user_id, token_id = await iam.check_token(session, token="sk-abcdef")

    assert (user_id, token_id) == (1, 2)


@pytest.mark.asyncio
async def test_check_token_invalid_or_expired(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    # invalid jwt
    with patch.object(iam, "_decode_token", side_effect=JWTError("bad")):
        uid, tid = await iam.check_token(session, token="sk-xxx")
        assert (uid, tid) == (None, None)

    # missing prefix / malformed
    with patch.object(iam, "_decode_token", side_effect=IndexError()):
        uid, tid = await iam.check_token(session, token="xxx")
        assert (uid, tid) == (None, None)

    # decoded but not found in DB (expired)
    with patch.object(iam, "_decode_token", return_value={"user_id": 1, "token_id": 2}):
        session.execute = AsyncMock(return_value=_Result(all_rows=[]))
        uid, tid = await iam.check_token(session, token="sk-abcdef")
        assert (uid, tid) == (None, None)


@pytest.mark.asyncio
async def test_invalidate_token_sets_now(session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    session.execute = AsyncMock(return_value=None)

    await iam.invalidate_token(session, token_id=1, user_id=2)
    session.commit.assert_awaited()
