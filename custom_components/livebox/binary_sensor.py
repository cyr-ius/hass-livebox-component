"""Livebox binary sensor entities."""
import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorEntity,
)

from .const import COORDINATOR, DOMAIN, LIVEBOX_ID, TEMPLATE_SENSOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]
    async_add_entities([WanStatus(coordinator, box_id)], True)


class WanStatus(BinarySensorEntity):
    """Representation of a livebox sensor."""

    device_class = DEVICE_CLASS_CONNECTIVITY

    def __init__(self, coordinator, box_id):
        """Initialize the sensor."""
        self.box_id = box_id
        self.coordinator = coordinator

    @property
    def name(self):
        """Return name sensor."""
        return "WAN Status"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        wstatus = self.coordinator.data.get("wan_status", {}).get("data", {})
        return wstatus.get("WanState") == "up"

    @property
    def unique_id(self):
        """Return unique_id."""
        return f"{self.box_id}_connectivity"

    @property
    def device_info(self):
        """Return the device info."""
        return {"identifiers": {(DOMAIN, self.box_id)}}

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        wstatus = self.coordinator.data.get("wan_status", {}).get("data", {})
        uptime = self.coordinator.data["infos"].get("UpTime")
        _attributs = {
            "link_type": wstatus.get("LinkType"),
            "link_state": wstatus.get("LinkState"),
            "last_connection_error": wstatus.get("LastConnectionError"),
            "wan_ipaddress": wstatus.get("IPAddress"),
            "wan_ipv6address": wstatus.get("IPv6Address"),
            "uptime": ConvertSectoDay(uptime),
        }
        cwired = self.coordinator.data.get("count_wired_devices")
        if cwired > 0:
            _attributs.update({"wired clients": cwired})
        cwireless = self.coordinator.data.get("count_wireless_devices")
        if cwireless > 0:
            _attributs.update({"wireless clients": cwireless})

        return _attributs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        self.coordinator.async_remove_listener(self.async_write_ha_state)

    async def async_update(self) -> None:
        """Update WLED entity."""
        await self.coordinator.async_request_refresh()


def ConvertSectoDay(n):
    return datetime.today() - timedelta(seconds=n)
