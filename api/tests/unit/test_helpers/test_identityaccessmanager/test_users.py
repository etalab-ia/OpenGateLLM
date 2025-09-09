import datetime as dt
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.utils.exceptions import (
    OrganizationNotFoundException,
    RoleNotFoundException,
    UserAlreadyExistsException,
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

    def scalar_one_or_none(self):
        # mirror SQLAlchemy behavior: raise if exception, otherwise return value (may be None)
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


@pytest.fixture
def iam():
    return IdentityAccessManager(master_key="secret")


@pytest.mark.asyncio
async def test_create_user_success(session: AsyncSession, iam: IdentityAccessManager):
    # role exists -> ok, organization None, insert -> returning id
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=10)])

    uid = await iam.create_user(
        session=session,
        email="alice@example.com",
        name="alice",
        role_id=1,
        organization_id=None,
        budget=12.5,
        expires_at=int(dt.datetime.now(tz=dt.UTC).timestamp()) + 100,
        sub="sub123",
    )

    assert uid == 10
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_user_role_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(RoleNotFoundException):
        await iam.create_user(session, email="bob@example.com", name="bob", role_id=9)


@pytest.mark.asyncio
async def test_create_user_organization_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=NoResultFound())])

    with pytest.raises(OrganizationNotFoundException):
        await iam.create_user(session, email="bob@example.com", name="bob", role_id=1, organization_id=5)


@pytest.mark.asyncio
async def test_create_user_unique_violation_to_400(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), IntegrityError("", "", None)])

    with pytest.raises(UserAlreadyExistsException):
        await iam.create_user(session, email="bob@example.com", name="bob", role_id=1)


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
async def test_get_user_info_master_user(iam: IdentityAccessManager, session: AsyncSession, monkeypatch):
    # When user_id is 0, returns master info with all permissions and all non-zero limits
    from types import SimpleNamespace

    # Provide a fake model_registry with models list to avoid NoneType error by patching the module variable used
    import api.helpers._identityaccessmanager as iam_mod
    from api.schemas.admin.roles import LimitType, PermissionType

    monkeypatch.setattr(iam_mod.global_context, "model_registry", SimpleNamespace(models=["gpt-4"]), raising=False)

    user = await iam.get_user_info(session=session, user_id=0)

    assert user.id == 0
    assert user.name == "master"
    assert user.email == "master"
    assert user.organization == 0
    assert set(user.permissions) == set(PermissionType)
    # limits list is built from global_context.model_registry.models; we only assert structure
    assert all(limit.value is None or limit.value >= 0 for limit in user.limits)
    assert all(limit.type in list(LimitType) for limit in user.limits)


@pytest.mark.asyncio
async def test_get_user_info_by_id_success(session: AsyncSession, iam: IdentityAccessManager):
    # Arrange get_users -> returns one user row with plain values
    mapping_user = {
        "id": 1,
        "name": "alice",
        "role": 2,
        "organization": None,
        "budget": 10.0,
        "expires_at": 123,
        "created_at": 10,
        "updated_at": 11,
        "email": "alice@example.com",
        "sub": None,
    }

    class _RowDict:
        def __init__(self, data: dict):
            self._data = data

        def _asdict(self):
            return dict(self._data)

    class _LimitRow:
        def __init__(self, role_id, model, type, value):
            self.role_id = role_id
            self.model = model
            self.type = type
            self.value = value

    class _PermissionRow:
        def __init__(self, role_id, permission):
            self.role_id = role_id
            self.permission = permission

    # Sequence: get_users -> roles rows, limits rows, permissions rows (get_roles won't fetch ids when role_id provided)
    roles_rows = [
        _RowDict({"id": 2, "name": "role", "created_at": 100, "updated_at": 101, "users": 1}),
    ]

    from api.schemas.admin.roles import LimitType, PermissionType

    limits_iter = [
        _LimitRow(2, "gpt-4", LimitType.TPM, 100),
    ]
    permissions_iter = [
        _PermissionRow(2, PermissionType.READ_METRIC),
    ]

    session.execute = AsyncMock(
        side_effect=[
            # get_users
            _Result(all_rows=[MagicMock(_mapping=mapping_user)]),
            # get_roles: roles rows
            _Result(all_rows=roles_rows),
            # get_roles: limits rows
            _Result(all_rows=None, iterate_rows=limits_iter),
            # get_roles: permissions rows
            _Result(all_rows=None, iterate_rows=permissions_iter),
        ]
    )

    # Act
    user = await iam.get_user_info(session=session, user_id=1)

    # Assert
    assert user.id == 1
    assert user.email == "alice@example.com"
    assert user.name == "alice"
    assert user.organization is None
    assert user.budget == 10.0
    assert user.expires_at == 123
    assert user.created_at == 10
    assert user.updated_at == 11
    assert len(user.permissions) == 1
    assert len(user.limits) == 1


@pytest.mark.asyncio
async def test_get_user_info_by_email_success(session: AsyncSession, iam: IdentityAccessManager):
    # Similar to by_id but call with email
    mapping_user = {
        "id": 5,
        "name": "bob",
        "role": 3,
        "organization": 9,
        "budget": None,
        "expires_at": None,
        "created_at": 20,
        "updated_at": 21,
        "email": "bob@example.com",
        "sub": None,
    }

    class _RowDict:
        def __init__(self, data: dict):
            self._data = data

        def _asdict(self):
            return dict(self._data)

    class _LimitRow:
        def __init__(self, role_id, model, type, value):
            self.role_id = role_id
            self.model = model
            self.type = type
            self.value = value

    class _PermissionRow:
        def __init__(self, role_id, permission):
            self.role_id = role_id
            self.permission = permission

    from api.schemas.admin.roles import LimitType, PermissionType

    # No ids page when role_id is provided to get_roles
    roles_rows = [
        _RowDict({"id": 3, "name": "role", "created_at": 200, "updated_at": 201, "users": 1}),
    ]
    limits_iter = [
        _LimitRow(3, "mistral", LimitType.RPM, 200),
    ]
    permissions_iter = [
        _PermissionRow(3, PermissionType.ADMIN),
    ]

    session.execute = AsyncMock(
        side_effect=[
            # get_users by email
            _Result(all_rows=[MagicMock(_mapping=mapping_user)]),
            # get_roles path without ids page
            _Result(all_rows=roles_rows),
            _Result(all_rows=None, iterate_rows=limits_iter),
            _Result(all_rows=None, iterate_rows=permissions_iter),
        ]
    )

    user = await iam.get_user_info(session=session, email="bob@example.com")

    assert user.id == 5
    assert user.email == "bob@example.com"
    assert user.name == "bob"
    assert user.organization == 9
    assert user.budget is None
    assert user.expires_at is None
    assert user.created_at == 20
    assert user.updated_at == 21
    assert any(p.value == "admin" for p in user.permissions)
    assert any(limit.model == "mistral" and limit.value == 200 for limit in user.limits)


@pytest.mark.asyncio
async def test_get_user_info_missing_params_raises(iam: IdentityAccessManager, session: AsyncSession):
    with pytest.raises(AssertionError):
        await iam.get_user_info(session=session)
