"""Livebox binary sensor entities."""
import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, LIVEBOX_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    datas = hass.data[DOMAIN][config_entry.entry_id]
    box_id = datas[LIVEBOX_ID]
    coordinator = datas[COORDINATOR]
    async_add_entities(
        [WanStatus(coordinator, box_id), CallMissed(coordinator, box_id)], True
    )


class WanStatus(CoordinatorEntity, BinarySensorEntity):
    """Wan status sensor."""

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
        uptime = datetime.today() - timedelta(
            seconds=self.coordinator.data["infos"].get("UpTime")
        )
        _attributs = {
            "link_type": wstatus.get("LinkType"),
            "link_state": wstatus.get("LinkState"),
            "last_connection_error": wstatus.get("LastConnectionError"),
            "wan_ipaddress": wstatus.get("IPAddress"),
            "wan_ipv6address": wstatus.get("IPv6Address"),
            "uptime": uptime,
        }
        cwired = self.coordinator.data.get("count_wired_devices")
        if cwired > 0:
            _attributs.update({"wired clients": cwired})
        cwireless = self.coordinator.data.get("count_wireless_devices")
        if cwireless > 0:
            _attributs.update({"wireless clients": cwireless})

        return _attributs


class CallMissed(CoordinatorEntity, BinarySensorEntity):
    """Call missed sensor."""

    def __init__(self, coordinator, box_id):
        """Initialize the sensor."""
        self.box_id = box_id
        self.coordinator = coordinator

    @property
    def unique_id(self):
        """Return unique_id."""
        return f"{self.box_id}_callmissed"

    @property
    def name(self):
        """Return name sensor."""
        return "Call missed"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return len(self.coordinator.data.get("cmissed")) > 0

    @property
    def device_info(self):
        """Return the device info."""
        return {"identifiers": {(DOMAIN, self.box_id)}}

    @property
    def device_state_attributes(self):
        """Return attributs."""
        return self.coordinator.data.get("cmissed")
