"""Livebox binary sensor entities."""
import logging

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorDevice,
)

from . import DATA_LIVEBOX, DOMAIN, ID_BOX
from .const import TEMPLATE_SENSOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[ID_BOX]
    bridge = datas[DATA_LIVEBOX]

    async_add_entities([WanStatus(bridge, box_id)], True)


class WanStatus(BinarySensorDevice):
    """Representation of a livebox sensor."""

    device_class = DEVICE_CLASS_CONNECTIVITY

    def __init__(self, bridge, box_id):
        """Initialize the sensor."""

        self._bridge = bridge
        self._box_id = box_id
        self._state = None
        self._state = {}

    @property
    def name(self):
        """Return name sensor."""

        return f"{TEMPLATE_SENSOR} Wan status"

    def is_on(self):
        """Return true if the binary sensor is on."""

        if self._state.get("WanState"):
            return self._state["WanState"] == "up"
        return None

    @property
    def unique_id(self):
        """Return unique_id."""

        return f"{self._box_id}_connectivity"

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
    def device_state_attributes(self):
        """Return the device state attributes."""

        return {
            "link_type": self._state.get("LinkType", None),
            "link_state": self._state.get("LinkState", None),
            "last_connection_error": self._state.get("LastConnectionError", None),
            "wan_ipaddress": self._state.get("IPAddress", None),
            "wan_ipv6address": self._state.get("IPv6Address", None),
        }

    async def async_update(self):
        """Fetch status from livebox."""
        data_status = await self._bridge.async_get_status()
        if data_status:
            self._state = data_status
