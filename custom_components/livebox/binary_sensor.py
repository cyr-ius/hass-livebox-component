"""Livebox binary sensor entities."""
import logging

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorDevice,
)

from .const import DOMAIN, LIVEBOX_ID, TEMPLATE_SENSOR, COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]    
    async_add_entities([WanStatus(coordinator, box_id)], True)


class WanStatus(BinarySensorDevice):
    """Representation of a livebox sensor."""

    device_class = DEVICE_CLASS_CONNECTIVITY

    def __init__(self, coordinator, box_id):
        """Initialize the sensor."""
        self.box_id = box_id
        self.coordinator = coordinator        
        self._state = coordinator.data.status

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

        return f"{self.box_id}_connectivity"

    @property
    def device_info(self):
        """Return the device info."""

        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": TEMPLATE_SENSOR,
            "via_device": (DOMAIN, self.box_id),
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

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.coordinator.async_add_listener(
            self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self.coordinator.async_remove_listener(
            self.async_write_ha_state
        )
