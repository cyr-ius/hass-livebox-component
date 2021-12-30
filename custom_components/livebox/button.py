"""Button for Livebox router."""
import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, LIVEBOX_API, LIVEBOX_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors."""
    box_id = hass.data[DOMAIN][config_entry.entry_id][LIVEBOX_ID]
    api = hass.data[DOMAIN][config_entry.entry_id][LIVEBOX_API]
    async_add_entities([RestartButton(box_id, api)], True)


class RestartButton(ButtonEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Livebox restart"

    def __init__(self, box_id, api):
        """Initialize the sensor."""
        self.box_id = box_id
        self._api = api
        self._attr_unique_id = f"{self.box_id}_restart"
        self._attr_device_class = ButtonDeviceClass.RESTART
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def device_info(self):
        """Return the device info."""
        return {"identifiers": {(DOMAIN, self.box_id)}}

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.async_add_executor_job(self._api.system.reboot)
