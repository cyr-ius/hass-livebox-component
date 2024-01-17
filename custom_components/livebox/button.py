"""Button for Livebox router."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RESTART_ICON, RING_ICON
from .coordinator import LiveboxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RestartButton(coordinator), RingButton(coordinator)], True)


class RestartButton(ButtonEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Livebox restart"
    _attr_icon = RESTART_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id}_restart"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.system.async_reboot()


class RingButton(ButtonEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Ring your phone"
    _attr_icon = RING_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator: LiveboxDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.unique_id}_ring"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.unique_id)}}

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.call.async_set_voiceapplication_ring()
