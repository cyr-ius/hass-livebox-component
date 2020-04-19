"""Sensor for Livebox router."""
import logging

from homeassistant.components.switch import SwitchDevice

from .const import DOMAIN, ID_BOX, DATA_LIVEBOX, TEMPLATE_SENSOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[ID_BOX]
    bridge = datas[DATA_LIVEBOX]

    async_add_entities([WifiSwitch(bridge, box_id)], True)


class WifiSwitch(SwitchDevice):
    """Representation of a livebox sensor."""

    def __init__(self, bridge, box_id):
        """Initialize the sensor."""
        self._bridge = bridge
        self._box_id = box_id
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Wifi switch"

    @property
    def unique_id(self):
        """Return unique_id."""
        return f"{self._box_id}_wifi"

    @property
    def device_info(self):
        """Return the device info."""

        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": TEMPLATE_SENSOR,
            "via_device": (DOMAIN, self._box_id),
        }

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        parameters = {"Enable": "true", "Status": "true"}
        await self._bridge.wifi.set_wifi(parameters)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        parameters = {"Enable": "false", "Status": "false"}
        await self._bridge.wifi.set_wifi(parameters)

    async def async_update(self):
        """Return update entry."""
        data_status = await self._bridge.async_get_wifi()
        if data_status:
            self._state = data_status["status"]["Enable"] == "true"
