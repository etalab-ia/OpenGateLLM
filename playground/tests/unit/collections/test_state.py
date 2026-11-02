from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.features.collections.models import Collection
from app.features.collections.state import CollectionsState


def make_state(**overrides):
    values = {
        "is_authenticated": True,
        "api_key": "test-key",
        "user_id": 7,
        "opengaterag_url": "http://rag:8000",
        "opengatellm_timeout": 10,
        "entities": [],
        "entities_loading": False,
        "load_error": "",
        "search_input": "",
        "search": "",
        "visibility_filter": "all",
        "page": 1,
        "per_page": 12,
        "has_next_page": False,
        "order_by_value": "updated",
        "order_direction_value": "desc",
        "entity_to_create": Collection(),
        "create_entity_loading": False,
        "is_create_dialog_open": True,
        "entity": Collection(),
        "edit_entity_loading": False,
        "entity_to_delete": Collection(),
        "delete_entity_loading": False,
    }
    values.update(overrides)
    state = SimpleNamespace(**values)
    state._format_collection = CollectionsState._format_collection.__get__(state)
    state._error_message = CollectionsState._error_message.__get__(state)
    state.load_entities = lambda: CollectionsState.load_entities.fn(state)
    return state


def collection_model(raw, **overrides):
    return Collection(**{**raw, "created": "2026-01-01 00:00", "updated": "2026-01-01 00:00", **overrides})


def response(data=None, status_code=200):
    return httpx.Response(status_code=status_code, json=data, request=httpx.Request("GET", "http://rag:8000"))


async def drive(events):
    return [event async for event in events]


@pytest.fixture
def mock_collection():
    return {
        "id": 42,
        "name": "Guides",
        "description": "Public procedures",
        "owner": 7,
        "visibility": "private",
        "documents": 3,
        "size": 1200,
        "created": 1767225600,
        "updated": 1767225600,
    }


@pytest.mark.asyncio
async def test_should_send_filters_and_page_size_plus_one(mock_collection):
    # Arrange
    state = make_state(search="Guides", visibility_filter="private", page=2)
    state._request = AsyncMock(return_value=response({"data": [mock_collection] * 13}))

    # Act
    await drive(CollectionsState.load_entities.fn(state))

    # Assert
    state._request.assert_awaited_once_with(
        "GET",
        "/v1/collections",
        params={
            "offset": 12,
            "limit": 13,
            "order_by": "updated",
            "order_direction": "desc",
            "name": "Guides",
            "visibility": "private",
        },
    )
    assert len(state.entities) == 12
    assert state.has_next_page is True
    assert state.entities[0].is_owner is True


@pytest.mark.asyncio
async def test_should_hide_mutation_actions_for_other_owners(mock_collection):
    # Arrange
    state = make_state()
    state._request = AsyncMock(return_value=response({"data": [{**mock_collection, "owner": 99, "visibility": "public"}]}))

    # Act
    await drive(CollectionsState.load_entities.fn(state))

    # Assert
    assert state.entities[0].is_owner is False
    CollectionsState.set_entity_settings.fn(state, state.entities[0])
    CollectionsState.set_entity_to_delete.fn(state, state.entities[0])
    assert state.entity.id is None
    assert state.entity_to_delete.id is None


@pytest.mark.asyncio
async def test_should_clear_stale_results_when_loading_fails(mock_collection):
    # Arrange
    state = make_state(entities=[collection_model(mock_collection, is_owner=True)], has_next_page=True)
    state._request = AsyncMock(return_value=response({"detail": "Authentication required"}, status_code=401))

    # Act
    await drive(CollectionsState.load_entities.fn(state))

    # Assert
    assert state.entities == []
    assert state.has_next_page is False
    assert state.entities_loading is False
    assert state.load_error == "Authentication required"


@pytest.mark.asyncio
async def test_should_create_private_collection_by_default():
    # Arrange
    state = make_state(entity_to_create=Collection(name="New collection"))
    state._request = AsyncMock(side_effect=[response({"id": 42}, status_code=201), response({"data": []})])

    # Act
    await drive(CollectionsState.create_entity.fn(state))

    # Assert
    assert state._request.await_args_list[0].args == ("POST", "/v1/collections")
    assert state._request.await_args_list[0].kwargs["json"] == {"name": "New collection", "description": None, "visibility": "private"}
    assert state.is_create_dialog_open is False
    assert state.create_entity_loading is False


@pytest.mark.asyncio
async def test_should_update_owned_collection_without_parsing_204_response(mock_collection):
    # Arrange
    state = make_state(entity=collection_model(mock_collection, name="Updated", is_owner=True))
    no_content = httpx.Response(204, request=httpx.Request("PATCH", "http://rag:8000/v1/collections/42"))
    state._request = AsyncMock(side_effect=[no_content, response({"data": []})])

    # Act
    await drive(CollectionsState.edit_entity.fn(state))

    # Assert
    assert state._request.await_args_list[0].args == ("PATCH", "/v1/collections/42")
    assert state._request.await_args_list[0].kwargs["json"] == {
        "name": "Updated",
        "description": "Public procedures",
        "visibility": "private",
    }
    assert state.entity.id is None
    assert state.edit_entity_loading is False


@pytest.mark.asyncio
async def test_should_delete_owned_collection_without_parsing_204_response(mock_collection):
    # Arrange
    state = make_state(entity_to_delete=collection_model(mock_collection, is_owner=True), entities=[collection_model(mock_collection, is_owner=True)])
    no_content = httpx.Response(204, request=httpx.Request("DELETE", "http://rag:8000/v1/collections/42"))
    state._request = AsyncMock(side_effect=[no_content, response({"data": []})])

    # Act
    await drive(CollectionsState.delete_entity.fn(state))

    # Assert
    state._request.assert_any_await("DELETE", "/v1/collections/42")
    assert state.entity_to_delete.id is None
    assert state.delete_entity_loading is False


@pytest.mark.asyncio
async def test_should_reject_mutation_for_other_owner(mock_collection):
    # Arrange
    state = make_state(entity=collection_model(mock_collection, is_owner=False))
    state._request = AsyncMock()

    # Act
    await drive(CollectionsState.edit_entity.fn(state))

    # Assert
    state._request.assert_not_awaited()
    assert state.entity.id == 42


@pytest.mark.asyncio
async def test_should_not_start_loading_after_logout():
    # Arrange
    state = make_state(is_authenticated=False, api_key=None)
    state._request = AsyncMock()

    # Act
    await drive(CollectionsState.load_entities.fn(state))

    # Assert
    state._request.assert_not_awaited()
    assert state.entities_loading is False
