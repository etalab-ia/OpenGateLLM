from abc import abstractmethod
from typing import Any

import reflex as rx

from app.features.auth.state import AuthState
from app.shared.models.entities import Entity


class EntityState(AuthState):
    """API Keys management state."""

    ############################################################
    # Load entities
    ############################################################
    entities: list[Entity] = []
    entities_loading: bool = False

    @rx.event
    @abstractmethod
    async def load_entities(self):
        """Load entities"""
        pass

    ############################################################
    # Create entity
    ############################################################
    new_entity_data: dict[str, Any] = {}
    create_entity_loading: bool = False

    @rx.event
    @abstractmethod
    async def create_entity(self):
        """Create an entity."""
        pass

    ############################################################
    # Delete entity
    ############################################################
    delete_entity_id: int | None = None
    delete_entity_loading: bool = False

    @rx.event
    @abstractmethod
    async def delete_entity(self):
        """Delete an entity."""
        pass

    @rx.event
    @abstractmethod
    def set_entity_to_delete(self, entity: Entity):
        """Set the entity to delete."""
        self.delete_entity_id = entity.id

    @rx.var
    def is_delete_entity_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        return self.delete_entity_id is not None

    @rx.event
    def handle_delete_entity_dialog_change(self, is_open: bool):
        """Handle delete entity dialog open/close state change."""
        if not is_open:
            self.delete_entity_id = None

    ############################################################
    # Entity settings
    ############################################################
    entity_id: int | None = None
    entity_settings_loading: bool = False

    @rx.event
    @abstractmethod
    async def edit_entity(self):
        """Update an entity."""
        pass

    @rx.event
    @abstractmethod
    def set_entity_settings(self, entity: Entity | None):
        """Set entity to edit and load its data."""
        pass

    @rx.var
    def is_settings_entity_dialog_open(self) -> bool:
        """Check if edit entity dialog should be open."""
        return self.entity_id is not None

    @rx.event
    def handle_settings_entity_dialog_change(self, is_open: bool):
        """Handle edit entity dialog open/close state change."""
        if not is_open:
            self.entity_id = None

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
