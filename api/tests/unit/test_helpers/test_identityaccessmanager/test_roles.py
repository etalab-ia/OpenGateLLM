import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.schemas.admin.roles import Limit, LimitType, PermissionType
from api.utils.exceptions import (
    DeleteRoleWithUsersException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
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


@pytest.fixture
def iam():
    return IdentityAccessManager(master_key="secret")


@pytest.mark.asyncio
async def test_create_role_success(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=123), None, None])

    role_id = await iam.create_role(
        session=session,
        name="analyst",
        limits=[Limit(model="gpt-4", type=LimitType.TPM, value=100)],
        permissions=[PermissionType.READ_METRIC],
    )

    assert role_id == 123
    assert session.commit.await_count == 2
    assert session.execute.await_count >= 3


@pytest.mark.asyncio
async def test_create_role_already_exists(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=IntegrityError("", "", None))

    with pytest.raises(RoleAlreadyExistsException):
        await iam.create_role(session=session, name="duplicate")


@pytest.mark.asyncio
async def test_delete_role_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(RoleNotFoundException):
        await iam.delete_role(session=session, role_id=999)


@pytest.mark.asyncio
async def test_delete_role_with_users_forbidden(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), IntegrityError("", "", None)])

    with pytest.raises(DeleteRoleWithUsersException):
        await iam.delete_role(session=session, role_id=1)


@pytest.mark.asyncio
async def test_update_role_noop(session: AsyncSession, iam: IdentityAccessManager):
    # First call: role exists
    session.execute = AsyncMock(return_value=_Result(scalar_one=MagicMock(id=1)))

    await iam.update_role(session=session, role_id=1)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_role_name_limits_permissions(session: AsyncSession, iam: IdentityAccessManager):
    # role exists
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=MagicMock(id=10)), None, None, None, None, None])

    await iam.update_role(
        session=session,
        role_id=10,
        name="power-user",
        limits=[
            Limit(model="gpt-4", type=LimitType.TPM, value=100),
            Limit(model="gpt-4", type=LimitType.RPM, value=200),
        ],
        permissions=[PermissionType.READ_METRIC, PermissionType.READ_METRIC],  # duplicate intentional
    )

    session.commit.assert_awaited()
    assert session.execute.await_count >= 6


class _RowDict:
    def __init__(self, data: dict):
        self._data = data

    def _asdict(self):
        return dict(self._data)


class _LimitRow:
    def __init__(self, role_id, model, type, value):  # noqa: A003 - match attribute names used by code
        self.role_id = role_id
        self.model = model
        self.type = type
        self.value = value


class _PermissionRow:
    def __init__(self, role_id, permission):
        self.role_id = role_id
        self.permission = permission


@pytest.mark.asyncio
async def test_get_roles_with_details(session: AsyncSession, iam: IdentityAccessManager):
    # Step 1: ids page
    ids_result = _Result(all_rows=[(1,), (2,)])
    # Step 2: roles with counts
    roles_rows = [
        _RowDict({"id": 1, "name": "admin", "created_at": 1, "updated_at": 2, "users": 3}),
        _RowDict({"id": 2, "name": "user", "created_at": 4, "updated_at": 5, "users": 0}),
    ]
    roles_result = _Result(all_rows=roles_rows)
    # Step 3: limits
    limits_iter = [
        _LimitRow(1, "gpt-4", LimitType.TPM, 100),
        _LimitRow(2, "gpt-4", LimitType.RPM, 200),
    ]
    limits_result = _Result(iterate_rows=limits_iter)
    # Step 4: permissions
    permissions_iter = [
        _PermissionRow(1, PermissionType.ADMIN),
        _PermissionRow(2, PermissionType.READ_METRIC),
    ]
    permissions_result = _Result(iterate_rows=permissions_iter)

    session.execute = AsyncMock(side_effect=[ids_result, roles_result, limits_result, permissions_result])

    roles = await iam.get_roles(session=session)

    assert len(roles) == 2
    first = next(r for r in roles if r.id == 1)
    assert first.users == 3
    assert any(limit.model == "gpt-4" and limit.type == LimitType.TPM for limit in first.limits)
    assert PermissionType.ADMIN in first.permissions


@pytest.mark.asyncio
async def test_get_roles_not_found_by_id(session: AsyncSession, iam: IdentityAccessManager):
    # Direct role query returns empty
    roles_result = _Result(all_rows=[])
    session.execute = AsyncMock(side_effect=[roles_result])

    with pytest.raises(RoleNotFoundException):
        await iam.get_roles(session=session, role_id=999)
