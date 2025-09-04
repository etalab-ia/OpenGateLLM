import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._identityaccessmanager import IdentityAccessManager
from api.utils.exceptions import OrganizationNotFoundException


class _Result:
    def __init__(self, scalar_one=None, all_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows

    def scalar_one(self):
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
async def test_create_organization_success(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=42))

    org_id = await iam.create_organization(session=session, name="org-a")

    assert org_id == 42
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delete_organization_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(OrganizationNotFoundException):
        await iam.delete_organization(session=session, organization_id=999)


@pytest.mark.asyncio
async def test_delete_organization_success(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=1), None])

    await iam.delete_organization(session=session, organization_id=1)
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_update_organization_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(scalar_one=NoResultFound()))

    with pytest.raises(OrganizationNotFoundException):
        await iam.update_organization(session=session, organization_id=10, name="new")


@pytest.mark.asyncio
async def test_update_organization_name(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(side_effect=[_Result(scalar_one=MagicMock(id=7)), None])

    await iam.update_organization(session=session, organization_id=7, name="renamed")

    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_get_organizations_pagination_and_filter(session: AsyncSession, iam: IdentityAccessManager):
    rows = [
        MagicMock(_mapping={"id": 1, "name": "A", "created_at": 1, "updated_at": 1}),
        MagicMock(_mapping={"id": 2, "name": "B", "created_at": 2, "updated_at": 3}),
    ]
    session.execute = AsyncMock(return_value=_Result(all_rows=rows))

    organizations = await iam.get_organizations(session=session, offset=0, limit=10)

    assert len(organizations) == 2
    assert organizations[0].id == 1


@pytest.mark.asyncio
async def test_get_organization_by_id_not_found(session: AsyncSession, iam: IdentityAccessManager):
    session.execute = AsyncMock(return_value=_Result(all_rows=[]))

    with pytest.raises(OrganizationNotFoundException):
        await iam.get_organizations(session=session, organization_id=404)
