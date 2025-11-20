import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

from jose import JWTError
import pytest
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
def postgres_session():
    return AsyncMock(spec=AsyncSession)


def _ts_now():
    return int(dt.datetime.now(tz=dt.UTC).timestamp())


@pytest.mark.asyncio
async def test_create_token_success_and_masking(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret", key_max_expiration_days=10)

    # user exists
    postgres_session.execute = AsyncMock()
    postgres_session.execute.side_effect = [
        _Result(scalar_one=MagicMock(id=1)),  # select user
        _Result(scalar_one=123),  # insert token, returning id
        None,  # update token with masked token
    ]

    with patch.object(iam, "_encode_token", return_value="sk-abc123456789xyz") as enc:
        token_id, app_token = await iam.create_token(postgres_session, user_id=1, name="dev", expires=_ts_now() + 100)

    assert token_id == 123
    assert app_token.startswith("sk-")
    enc.assert_called_once()
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_token_user_not_found(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(UserNotFoundException):
        await iam.create_token(postgres_session, user_id=99, name="dev")


@pytest.mark.asyncio
async def test_create_token_invalid_expiration_window(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret", key_max_expiration_days=1)
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=MagicMock(id=1)))

    too_far = _ts_now() + 3 * 86400

    with pytest.raises(InvalidTokenExpirationException):
        await iam.create_token(postgres_session, user_id=1, name="dev", expires=too_far)


@pytest.mark.asyncio
async def test_refresh_token_updates_usage_and_deletes_old(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    # old tokens with same name
    postgres_session.execute = AsyncMock()
    postgres_session.execute.side_effect = [
        _Result(all_rows=[(10,), (11,)]),  # select old token ids
        _Result(scalar_one=MagicMock(id=1)),  # select user in create_token
        _Result(scalar_one=100),  # insert new token id
        None,  # update new token with masked token
        None,  # update usage set token_id to new
        None,  # delete old tokens
    ]

    with patch.object(iam, "_encode_token", return_value="sk-newtoken"):
        new_id, app_token = await iam.refresh_token(postgres_session, user_id=1, name="dev")

    assert new_id == 100
    assert app_token == "sk-newtoken"
    assert postgres_session.commit.await_count >= 2


@pytest.mark.asyncio
async def test_delete_token_not_found(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(TokenNotFoundException):
        await iam.delete_token(postgres_session, user_id=1, token_id=9)


@pytest.mark.asyncio
async def test_delete_token_success(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), None])

    await iam.delete_token(postgres_session, user_id=1, token_id=2)
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_tokens_by_name(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(return_value=None)
    await iam.delete_tokens(postgres_session, user_id=1, name="ci")
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_tokens_filters_and_exclude_expired(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    rows = [
        MagicMock(_mapping={"id": 1, "name": "dev", "token": "sk-xxxx", "user": 1, "expires": None, "created": 10}),
        MagicMock(_mapping={"id": 2, "name": "ops", "token": "sk-yyyy", "user": 1, "expires": 11, "created": 12}),
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    tokens = await iam.get_tokens(postgres_session, user_id=1, exclude_expired=True)

    assert len(tokens) == 2
    assert tokens[0].user == 1


@pytest.mark.asyncio
async def test_get_token_by_id_not_found(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(TokenNotFoundException):
        await iam.get_tokens(postgres_session, token_id=404)


@pytest.mark.asyncio
async def test_check_token_ok(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    with patch.object(iam, "_decode_token", return_value={"user_id": 1, "token_id": 2}):
        postgres_session.execute = AsyncMock(
            return_value=_Result(
                all_rows=[
                    MagicMock(
                        _mapping={
                            "id": 2,
                            "user": 1,
                            "token": "sk-abcdef",
                            "name": "dev",
                            "created": 1755243926,
                            "expires": None,
                        }
                    )
                ]
            )
        )
        user_id, token_id, token_name = await iam.check_token(postgres_session, token="sk-abcdef")

    assert (user_id, token_id, token_name) == (1, 2, "dev")


@pytest.mark.asyncio
async def test_check_token_invalid_or_expired(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")

    # invalid jwt
    with patch.object(iam, "_decode_token", side_effect=JWTError("bad")):
        uid, tid, token_name = await iam.check_token(postgres_session, token="sk-xxx")
        assert (uid, tid, token_name) == (None, None, None)

    # missing prefix / malformed
    with patch.object(iam, "_decode_token", side_effect=IndexError()):
        uid, tid, token_name = await iam.check_token(postgres_session, token="xxx")
        assert (uid, tid, token_name) == (None, None, None)

    # decoded but not found in DB (expired)
    with patch.object(iam, "_decode_token", return_value={"user_id": 1, "token_id": 2}):
        postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))
        uid, tid, token_name = await iam.check_token(postgres_session, token="sk-abcdef")
        assert (uid, tid, token_name) == (None, None, None)


@pytest.mark.asyncio
async def test_invalidate_token_sets_now(postgres_session: AsyncSession):
    iam = IdentityAccessManager(master_key="secret")
    postgres_session.execute = AsyncMock(return_value=None)

    await iam.invalidate_token(postgres_session, token_id=1, user_id=2)
    postgres_session.commit.assert_awaited()
