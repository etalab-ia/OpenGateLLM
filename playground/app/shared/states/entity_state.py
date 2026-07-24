from abc import abstractmethod
import math

import reflex as rx

from app.features.auth.state import AuthState
from app.shared.models.entities import Entity


class EntityState(AuthState):
    """API Keys management state."""

    ############################################################
    # Load entities
    ############################################################
    # entities: list[Entity] = []
    entities_loading: bool = False

    @abstractmethod
    async def load_entities(self):
        """Load entities"""
        pass

    ############################################################
    # Create entity
    ############################################################
    # entity_to_create: Entity = Entity()
    create_entity_loading: bool = False

    @abstractmethod
    def set_entity_to_create(self, entity: Entity):
        """Set entity to create."""
        pass

    @abstractmethod
    def set_new_entity_attribut(self, attribute: str, value: str | None):
        """Set new entity attributes."""
        pass

    ############################################################
    # Delete entity
    ############################################################
    # entity_to_delete: Entity = Entity()
    delete_entity_loading: bool = False

    @abstractmethod
    async def delete_entity(self):
        """Delete an entity."""
        pass

    @abstractmethod
    def set_entity_to_delete(self, entity: Entity):
        """Set the entity to delete."""
        pass

    @abstractmethod
    def is_delete_entity_dialog_open(self) -> bool:
        """Check if delete dialog should be open."""
        pass

    @abstractmethod
    def handle_delete_entity_dialog_change(self, is_open: bool):
        """Handle delete entity dialog open/close state change."""
        pass

    ############################################################
    # Entity settings
    ############################################################
    edit_entity_loading: bool = False

    @abstractmethod
    def is_settings_entity_dialog_open(self) -> bool:
        """Check if edit entity dialog should be open."""
        pass

    @abstractmethod
    def handle_settings_entity_dialog_change(self, is_open: bool):
        """Handle edit entity dialog open/close state change."""
        pass

    @abstractmethod
    async def edit_entity(self):
        """Update an entity."""
        pass

    @abstractmethod
    def set_entity_settings(self, entity: Entity):
        """Set entity to edit and load its data."""
        pass

    @abstractmethod
    def set_edit_entity_attribut(self, attribute: str, value: str | None):
        """Set edit entity attributes."""
        pass

    ############################################################
    # Pagination
    ############################################################
    total: int = 0
    page: int = 1
    per_page: int = 20

    @abstractmethod
    async def set_order_by(self, value: str):
        """Set order by field and reload."""
        pass

    @abstractmethod
    async def set_order_direction(self, value: str):
        """Set order direction and reload."""
        pass

    @rx.event
    async def prev_page(self):
        """Go to previous page."""
        if self.page > 1:
            self.page -= 1
            yield
            async for _ in self.load_entities():
                yield

    @rx.event
    async def next_page(self):
        """Go to next page."""
        if self.has_more_page:
            self.page += 1
            yield
            async for _ in self.load_entities():
                yield

    @rx.var
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.per_page))

    @rx.var
    def has_more_page(self) -> bool:
        return self.page < self.total_pages
