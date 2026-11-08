"""Parent Entity."""

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LiveboxDataUpdateCoordinator


class LiveboxEntity(CoordinatorEntity[LiveboxDataUpdateCoordinator]):
    """Base class for all entities."""

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
        if not isinstance(self.device_entry, dr.DeviceEntry):
            return
        via_device_id = self.coordinator.get_parent_device_id(device_key)
        if via_device_id is None or via_device_id == self.device_entry.via_device_id:
            return
        if device_entry := dr.async_get(self.hass).async_update_device(
            self.device_entry.id, via_device_id=via_device_id
        ):
            self.device_entry = device_entry

    def _client_device_info(self, device_key: str, name: str | None) -> DeviceInfo:
        """Return the device info of a Livebox client, linked to its parent."""
        device_info = DeviceInfo(name=name, identifiers={(DOMAIN, device_key)})
        if via_device_id := self.coordinator.get_parent_device_id(device_key):
            device_info["via_device_id"] = via_device_id
        return device_info
