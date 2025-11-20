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
def postgres_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def iam():
    return IdentityAccessManager(master_key="secret")


@pytest.mark.asyncio
async def test_create_user_success(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # role exists -> ok, organization None, insert -> returning id
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=10)])

    uid = await iam.create_user(
        postgres_session=postgres_session,
        email="alice@example.com",
        name="alice",
        role_id=1,
        organization_id=None,
        budget=12.5,
        expires=int(dt.datetime.now(tz=dt.UTC).timestamp()) + 100,
        sub="sub123",
    )

    assert uid == 10
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_user_role_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(RoleNotFoundException):
        await iam.create_user(postgres_session, email="bob@example.com", name="bob", role_id=9)


@pytest.mark.asyncio
async def test_create_user_organization_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), _Result(scalar_one=NoResultFound())])

    with pytest.raises(OrganizationNotFoundException):
        await iam.create_user(postgres_session, email="bob@example.com", name="bob", role_id=1, organization_id=5)


@pytest.mark.asyncio
async def test_create_user_unique_violation_to_400(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), IntegrityError("", "", None)])

    with pytest.raises(UserAlreadyExistsException):
        await iam.create_user(postgres_session, email="bob@example.com", name="bob", role_id=1)


@pytest.mark.asyncio
async def test_delete_user_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(UserNotFoundException):
        await iam.delete_user(postgres_session, user_id=404)


@pytest.mark.asyncio
async def test_delete_user_success(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), None])
    await iam.delete_user(postgres_session, user_id=1)
    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_user_success_all_fields(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # select user with join role
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires=None, role="role")]),
            _Result(scalar_one=1),  # check new role exists when different
            _Result(scalar_one=1),  # check organization exists
            None,  # update
        ]
    )

    await iam.update_user(
        postgres_session=postgres_session,
        user_id=1,
        name="alice2",
        role_id=2,
        organization_id=3,
        budget=100.0,
        expires=int(dt.datetime.now(tz=dt.UTC).timestamp()) + 100,
    )

    postgres_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_user_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(UserNotFoundException):
        await iam.update_user(postgres_session, user_id=123)


@pytest.mark.asyncio
async def test_update_user_role_missing(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires=None, role="role")]),
            _Result(scalar_one=NoResultFound()),
        ]
    )

    with pytest.raises(RoleNotFoundException):
        await iam.update_user(postgres_session, user_id=1, role_id=9)


@pytest.mark.asyncio
async def test_update_user_org_missing(postgres_session: AsyncSession, iam: IdentityAccessManager):
    postgres_session.execute = AsyncMock(
        side_effect=[
            _Result(all_rows=[MagicMock(id=1, name="alice", role_id=1, budget=None, expires=None, role="role")]),
            _Result(scalar_one=NoResultFound()),  # organization lookup -> not found
        ]
    )

    with pytest.raises(OrganizationNotFoundException):
        await iam.update_user(postgres_session, user_id=1, role_id=1, organization_id=999)


@pytest.mark.asyncio
async def test_get_users_filters_and_not_found(postgres_session: AsyncSession, iam: IdentityAccessManager):
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 10,
                "updated": 11,
                "email": "alice@example.com",
                "sub": "sub",
                "priority": 0,
            }
        )
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    users = await iam.get_users(postgres_session, role_id=1)
    assert len(users) == 1
    assert users[0].name == "alice"

    # not found by id
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))
    with pytest.raises(UserNotFoundException):
        await iam.get_users(postgres_session, user_id=404)


@pytest.mark.asyncio
async def test_get_user_info_master_user(iam: IdentityAccessManager, postgres_session: AsyncSession, monkeypatch):
    # When user_id is 0, returns master info with all permissions and all non-zero limits
    from types import SimpleNamespace

    # Provide a fake model_registry with async get_routers returning routers with ids
    import api.helpers._identityaccessmanager as iam_mod
    from api.schemas.admin.roles import LimitType, PermissionType

    class _Router:
        def __init__(self, router_id: int):
            self.id = router_id

    original_user_info = iam_mod.UserInfo

    class _UserInfo(original_user_info):
        def __init__(self, **kwargs):
            kwargs.setdefault("created", 0)
            kwargs.setdefault("updated", 0)
            super().__init__(**kwargs)

    monkeypatch.setattr(
        iam_mod.global_context,
        "model_registry",
        SimpleNamespace(get_routers=AsyncMock(return_value=[_Router(1)])),
        raising=False,
    )
    monkeypatch.setattr(iam_mod, "UserInfo", _UserInfo, raising=False)

    user = await iam.get_user_info(postgres_session=postgres_session, user_id=0)

    assert user.id == 0
    assert user.name == "master"
    assert user.email == "master"
    assert user.organization == 0
    assert set(user.permissions) == set(PermissionType)
    # limits list is built from global_context.model_registry.models; we only assert structure
    assert all(limit.value is None or limit.value >= 0 for limit in user.limits)
    assert all(limit.type in list(LimitType) for limit in user.limits)
    assert user.created == 0
    assert user.updated == 0


@pytest.mark.asyncio
async def test_get_user_info_by_id_success(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange get_users -> returns one user row with plain values
    mapping_user = {
        "id": 1,
        "name": "alice",
        "role": 2,
        "organization": None,
        "budget": 10.0,
        "expires": 123,
        "created": 10,
        "updated": 11,
        "email": "alice@example.com",
        "sub": None,
        "priority": 0,
    }

    class _RowDict:
        def __init__(self, data: dict):
            self._data = data

        def _asdict(self):
            return dict(self._data)

    class _LimitRow:
        def __init__(self, role_id, router_id, type, value):
            self.role_id = role_id
            self.router_id = router_id
            self.type = type
            self.value = value

    class _PermissionRow:
        def __init__(self, role_id, permission):
            self.role_id = role_id
            self.permission = permission

    # Sequence: get_users -> roles rows, limits rows, permissions rows (get_roles won't fetch ids when role_id provided)
    roles_rows = [
        _RowDict({"id": 2, "name": "role", "created": 100, "updated": 101, "users": 1}),
    ]

    from api.schemas.admin.roles import LimitType, PermissionType

    limits_iter = [_LimitRow(2, 101, LimitType.TPM, 100)]
    permissions_iter = [
        _PermissionRow(2, PermissionType.READ_METRIC),
    ]

    postgres_session.execute = AsyncMock(
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
    user = await iam.get_user_info(postgres_session=postgres_session, user_id=1)

    # Assert
    assert user.id == 1
    assert user.email == "alice@example.com"
    assert user.name == "alice"
    assert user.organization is None
    assert user.budget == 10.0
    assert user.expires == 123
    assert user.created == 10
    assert user.updated == 11
    assert len(user.permissions) == 1
    assert len(user.limits) == 1


@pytest.mark.asyncio
async def test_get_user_info_by_email_success(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Similar to by_id but call with email
    mapping_user = {
        "id": 5,
        "name": "bob",
        "role": 3,
        "organization": 9,
        "budget": None,
        "expires": None,
        "created": 20,
        "updated": 21,
        "email": "bob@example.com",
        "sub": None,
        "priority": 0,
    }

    class _RowDict:
        def __init__(self, data: dict):
            self._data = data

        def _asdict(self):
            return dict(self._data)

    class _LimitRow:
        def __init__(self, role_id, router_id, type, value):
            self.role_id = role_id
            self.router_id = router_id
            self.type = type
            self.value = value

    class _PermissionRow:
        def __init__(self, role_id, permission):
            self.role_id = role_id
            self.permission = permission

    from api.schemas.admin.roles import LimitType, PermissionType

    # No ids page when role_id is provided to get_roles
    roles_rows = [
        _RowDict({"id": 3, "name": "role", "created": 200, "updated": 201, "users": 1}),
    ]
    limits_iter = [_LimitRow(3, 202, LimitType.RPM, 200)]
    permissions_iter = [
        _PermissionRow(3, PermissionType.ADMIN),
    ]

    postgres_session.execute = AsyncMock(
        side_effect=[
            # get_users by email
            _Result(all_rows=[MagicMock(_mapping=mapping_user)]),
            # get_roles path without ids page
            _Result(all_rows=roles_rows),
            _Result(all_rows=None, iterate_rows=limits_iter),
            _Result(all_rows=None, iterate_rows=permissions_iter),
        ]
    )

    user = await iam.get_user_info(postgres_session=postgres_session, email="bob@example.com")

    assert user.id == 5
    assert user.email == "bob@example.com"
    assert user.name == "bob"
    assert user.organization == 9
    assert user.budget is None
    assert user.expires is None
    assert user.created == 20
    assert user.updated == 21
    assert any(p.value == "admin" for p in user.permissions)
    assert any(limit.router == 202 and limit.type == LimitType.RPM and limit.value == 200 for limit in user.limits)


@pytest.mark.asyncio
async def test_get_user_info_missing_params_raises(iam: IdentityAccessManager, postgres_session: AsyncSession):
    with pytest.raises(AssertionError):
        await iam.get_user_info(postgres_session=postgres_session)


@pytest.mark.asyncio
async def test_get_users_with_id_and_role_id(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 10,
                "updated": 11,
                "email": "alice@example.com",
                "sub": "sub",
                "priority": 0,
            }
        )
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    # Act
    users = await iam.get_users(postgres_session, user_id=1, role_id=1)

    # Assert
    assert len(users) == 1
    assert users[0].name == "alice"


@pytest.mark.asyncio
async def test_get_users_with_role_id_only(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 10,
                "updated": 11,
                "email": "alice@example.com",
                "sub": "sub",
                "priority": 0,
            }
        ),
        MagicMock(
            _mapping={
                "id": 2,
                "name": "bob",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 20,
                "updated": 21,
                "email": "bob@example.com",
                "sub": "sub",
                "priority": 0,
            }
        ),
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    # Act
    users = await iam.get_users(postgres_session, role_id=1)

    # Assert
    assert len(users) == 2


@pytest.mark.asyncio
async def test_get_users_with_id_only(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 10,
                "updated": 11,
                "email": "alice@example.com",
                "sub": "sub",
                "priority": 0,
            }
        )
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    # Act
    users = await iam.get_users(postgres_session, user_id=1)

    # Assert
    assert len(users) == 1
    assert users[0].name == "alice"


@pytest.mark.asyncio
async def test_get_users_no_params(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange
    rows = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "alice",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 10,
                "updated": 11,
                "email": "alice@example.com",
                "sub": "sub",
                "priority": 0,
            }
        ),
        MagicMock(
            _mapping={
                "id": 2,
                "name": "bob",
                "role": 1,
                "organization": None,
                "budget": None,
                "expires": None,
                "created": 20,
                "updated": 21,
                "email": "bob@example.com",
                "sub": "sub",
                "priority": 0,
            }
        ),
    ]
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    # Act
    users = await iam.get_users(postgres_session)

    # Assert
    assert len(users) == 2
    assert users[0].name == "alice"
    assert users[1].name == "bob"


@pytest.mark.asyncio
async def test_get_users_empty_result(postgres_session: AsyncSession, iam: IdentityAccessManager):
    # Arrange
    postgres_session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    # Act / Assert
    with pytest.raises(UserNotFoundException):
        await iam.get_users(postgres_session, user_id=404)
