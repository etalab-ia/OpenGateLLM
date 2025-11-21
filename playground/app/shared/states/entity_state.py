from abc import abstractmethod
from typing import Any

import reflex as rx

from app.features.auth.state import AuthState


class EntityState(AuthState):
    """API Keys management state."""

    ############################################################
    # Load entities
    ############################################################
    entities: list[Any] = []
    entities_loading: bool = False

    @rx.event
    @abstractmethod
    async def load_entities(self):
        pass

    ############################################################
    # Create entity
    ############################################################
    new_entity_data: dict[str, Any] = {}
    create_entity_loading: bool = False

    @rx.event
    @abstractmethod
    async def create_entity(self):
        pass

    ############################################################
    # Delete entity
    ############################################################
    entity_to_delete: int | None = None
    delete_entity_loading: bool = False

    @rx.event
    @abstractmethod
    async def delete_entity(self, entity_id: int):
        """Delete an API key."""
        pass

    @rx.var
    def is_delete_entity_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        return self.entity_to_delete is not None

    @rx.event
    def handle_delete_entity_dialog_change(self, is_open: bool):
        """Handle delete entity dialog open/close state change."""
        if not is_open:
            self.entity_to_delete = None

    ############################################################
    # Edit entity
    ############################################################
    entity_to_edit: int | None = None
    edit_entity_loading: bool = False

    @rx.event
    @abstractmethod
    async def update_entity(self):
        """Update an entity."""
        pass

    @rx.event
    @abstractmethod
    def set_entity_to_edit(self, entity_id: int | None):
        """Set entity to edit and load its data."""
        pass

    @rx.event
    def set_entity_to_delete(self, entity_id: int | None):
        """Set the entity to delete."""
        self.entity_to_delete = entity_id

    @rx.var
    def is_edit_entity_dialog_open(self) -> bool:
        """Check if edit entity dialog should be open."""
        return self.entity_to_edit is not None

    ############################################################
    # Pagination
    ############################################################
    page: int = 1
    per_page: int = 20
    has_more_page: bool = False
    order_by: str = "id"
    order_direction: str = "asc"

    @rx.event
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        self.order_by = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        self.order_direction = value
        self.page = 1
        self.has_more_page = False
        yield
        async for _ in self.load_entities():
            yield

    @rx.event
    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_entities():
                yield

    @rx.event
    async def next_page(self):
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_entities():
                yield
