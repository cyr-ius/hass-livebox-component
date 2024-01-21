"""Parent Entity."""
from __future__ import annotations

import logging

from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USE_TLS, DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class LiveboxEntity(CoordinatorEntity[LiveboxDataUpdateCoordinator], Entity):
    """Base class for all entities."""

    entity_description: EntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        entry = coordinator.config_entry
        infos = coordinator.data.get("infos", {})
        scheme = "https" if entry.data.get(CONF_USE_TLS) else "http"

        self._attr_unique_id = f"{coordinator.unique_id}-{entity_description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.unique_id)},
            "manufacturer": infos.get("Manufacturer"),
            "name": infos.get("ProductClass", DOMAIN.capitalize()),
            "model": infos.get("ModelName"),
            "sw_version": infos.get("SoftwareVersion"),
            "configuration_url": f"{scheme}://{entry.data.get('host')}:{entry.data.get('port')}",
        }
