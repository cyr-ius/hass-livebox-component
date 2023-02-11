"""Sensor for Livebox router."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, LIVEBOX_API, LIVEBOX_ID, GUESTWIFI_ICON

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    api = datas[LIVEBOX_API]
    coordinator = datas[COORDINATOR]
    async_add_entities([WifiSwitch(coordinator, box_id, api)], True)
    async_add_entities([GuestWifiSwitch(coordinator, box_id, api)], True)


class WifiSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Wifi switch"

    def __init__(self, coordinator, box_id, api):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{box_id}_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data.get("wifi")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.hass.async_add_executor_job(self._api.wifi.set_wifi, parameters)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.hass.async_add_executor_job(self._api.wifi.set_wifi, parameters)
        await self.coordinator.async_request_refresh()

class GuestWifiSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a livebox sensor."""

    _attr_name = "Guest Wifi switch"
    _attr_icon = GUESTWIFI_ICON

    def __init__(self, coordinator, box_id, api):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{box_id}_guest_wifi"
        self._attr_device_info = {"identifiers": {(DOMAIN, box_id)}}

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.coordinator.data.get("guest_wifi")

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self.hass.async_add_executor_job(self._api.guestwifi.set_guest_wifi, parameters)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self.hass.async_add_executor_job(self._api.guestwifi.set_guest_wifi, parameters)
        await self.coordinator.async_request_refresh()
