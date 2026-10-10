"""Parent Entity."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator


class LiveboxEntity(CoordinatorEntity[LiveboxDataUpdateCoordinator]):
    """Base class for all entities."""

    entity_description: EntityDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: LiveboxDataUpdateCoordinator, description: EntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description

        data = coordinator.data or {}
        unique_id = coordinator.unique_id or DOMAIN

        self._unique_name = data.get("infos", {}).get("ProductClass", DOMAIN)

        self._attr_unique_id = f"{unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @callback
    def _async_update_via_device(self, device_key: str | None) -> None:
        """Re-link the registry device when its parent changes (topology, roaming)."""
        if self.device_entry is None:
            return
        via_device_id = self.coordinator.get_parent_device_id(device_key)
        if via_device_id is None or via_device_id == self.device_entry.via_device_id:
            return
        if device_entry := dr.async_get(self.hass).async_update_device(
            self.device_entry.id, via_device_id=via_device_id
        ):
            self.device_entry = device_entry
